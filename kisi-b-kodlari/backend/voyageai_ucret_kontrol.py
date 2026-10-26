"""VoyageAI 2. hafta: fiyat kontrol CSV olustur ve yalniz kaynakli onayli fiyatlari isle.

backend klasorunde:
  python voyageai_ucret_kontrol.py           # inceleme CSV'sini olustur
  python voyageai_ucret_kontrol.py --apply   # doldurulan fiyatlari aday tablosuna isle

NOT: Fiyatlar bulunduklari para biriminde tutulur; ana tablonun tek para birimi
varsayimi dogrulanmadan 'yerler' tablosuna kopyalanmaz.
"""
import csv
import sys
from pathlib import Path
from urllib.parse import quote_plus
from sqlalchemy import text
from database import SessionLocal

FILE = Path(__file__).with_name('voyageai_ucret_inceleme.csv')
FIELDS = ['id','sehir','ad','kategori','osm_kaynak','fiyat_arama','ucret_turu','tutar','para_birimi','fiyat_kaynagi','kontrol_tarihi','aciklama']


def export():
    with SessionLocal() as db:
        rows = db.execute(text('''
            SELECT id,sehir_adi,ad,kategori,osm_kaynak
              FROM yeni_yer_adaylari
             ORDER BY sehir_adi,ad
        ''')).mappings().all()
    with FILE.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for r in rows:
            writer.writerow({
                'id':r['id'], 'sehir':r['sehir_adi'], 'ad':r['ad'],
                'kategori':r['kategori'], 'osm_kaynak':r['osm_kaynak'],
                'fiyat_arama':'https://www.google.com/search?q='+quote_plus(f"{r['ad']} {r['sehir_adi']} official ticket price"),
                'ucret_turu':'bilinmiyor', 'tutar':'', 'para_birimi':'',
                'fiyat_kaynagi':'', 'kontrol_tarihi':'', 'aciklama':''
            })
    print(f'HAZIR: {len(rows)} fiyat kontrol satiri -> {FILE.name}')
    print('Bilinmeyen ucretler bos birakildi. Veritabanina fiyat yazilmadi.')


def apply():
    if not FILE.exists():
        raise SystemExit('Once parametresiz calistirarak CSV olusturun.')
    with FILE.open(newline='',encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    seen=set(); approved=[]
    for r in rows:
        id_ = int(r['id'])
        if id_ in seen:
            raise ValueError(f'Tekrarlanan aday id: {id_}')
        seen.add(id_)
        status=(r['ucret_turu'] or '').strip().lower()
        if status=='bilinmiyor':
            continue
        if status not in ('ucretsiz','ucretli'):
            raise ValueError(f'{id_}: ucret_turu bilinmiyor/ucretsiz/ucretli olmali')
        source=(r['fiyat_kaynagi'] or '').strip()
        date=(r['kontrol_tarihi'] or '').strip()
        currency=(r['para_birimi'] or '').strip().upper()
        value=(r['tutar'] or '').strip().replace(',','.')
        if not source.startswith('https://') or not date:
            raise ValueError(f'{id_}: kaynak (https://) ve kontrol_tarihi zorunlu')
        if status=='ucretsiz':
            if value not in ('','0','0.0','0.00'):
                raise ValueError(f'{id_}: ucretsiz fiyat 0 olmali')
            val='0'
        else:
            from decimal import Decimal
            try: val=str(Decimal(value))
            except Exception: raise ValueError(f'{id_}: fiyat sayi olmali')
            if Decimal(val)<=0: raise ValueError(f'{id_}: ucretli fiyat pozitif olmali')
        if currency not in ('TRY','EUR'):
            raise ValueError(f'{id_}: para_birimi TRY veya EUR olmalı')
        approved.append({'id':id_,'fiyat':val,'tur':status,'currency':currency,'source':source,'date':date})
    with SessionLocal.begin() as db:
        db.execute(text('''ALTER TABLE yeni_yer_adaylari ADD COLUMN IF NOT EXISTS ucret_para_birimi text'''))
        db.execute(text('''ALTER TABLE yeni_yer_adaylari ADD COLUMN IF NOT EXISTS ucret_kaynagi text'''))
        db.execute(text('''ALTER TABLE yeni_yer_adaylari ADD COLUMN IF NOT EXISTS ucret_kontrol_tarihi date'''))
        db.execute(text('''ALTER TABLE yeni_yer_adaylari ADD COLUMN IF NOT EXISTS ucret_turu text'''))
        for r in approved:
            result=db.execute(text('''
                UPDATE yeni_yer_adaylari
                   SET ortalama_ucret=:fiyat, ucret_turu=:tur, ucret_para_birimi=:currency,
                       ucret_kaynagi=:source, ucret_kontrol_tarihi=CAST(:date AS date)
                 WHERE id=:id
            '''),r)
            if result.rowcount!=1: raise ValueError(f"Aday bulunamadi: {r['id']}")
    print(f'ISLENDI: {len(approved)} kaynakli fiyat. Kalanlar bilinmiyor.')
    print('Ana yerler tablosu ve kayit_onayi degistirilmedi.')

if __name__ == '__main__':
    if len(sys.argv)==1: export()
    elif sys.argv[1:]==['--apply']: apply()
    else: raise SystemExit('Kullanim: python voyageai_ucret_kontrol.py [--apply]')
