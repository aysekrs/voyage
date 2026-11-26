"""VoyageAI: optionally import 93 source-consistent OSM POI positions.

Source coordinate/name agreement is NOT independent verification of entrance location.
This script prints a dry-run, excludes all ambiguous records, and requires a
specific explicit confirmation before changing the database. It keeps candidate
status/provenance unchanged and never overwrites populated main coordinates.
"""
from __future__ import annotations
import csv
import math
from collections import Counter
from pathlib import Path
from sqlalchemy import text
from database import SessionLocal

BASE = Path(__file__).resolve().parent
SRC = BASE / 'VoyageAI_98_OSM_Eslesme_Incele.csv'
REPORT = BASE / 'VoyageAI_93_Aktarim_Sonucu.csv'
FIELDS = ['yer_id','ulke','sehir','gezilecek_yer','sonuc']

def norm(v):
    return str(v or '').strip().replace('İ','i').replace('I','ı').casefold()

def num(v):
    return float(str(v or '').strip().replace(',', '.'))


def main():
    if not SRC.is_file():
        raise SystemExit(f'CSV bulunamadi: {SRC}')
    with SRC.open(encoding='utf-8-sig',newline='') as f:
        rd=csv.DictReader(f,delimiter=';')
        records=list(rd)
    if len(records)!=98:
        raise SystemExit(f'Beklenen 98 kaynak kaydi yerine {len(records)} var; islem durduruldu.')
    ids=[r['yer_id'].strip() for r in records]
    if len(set(ids)) != len(ids):
        raise SystemExit('Tekrarlanan ID var; islem durduruldu.')

    db=SessionLocal()
    results=[]
    plan=[]
    try:
        existing=db.execute(text('''
            SELECT y.yer_id,y.ad AS yer_adi,s.ad AS sehir,s.ulke,
                   y.enlem AS ana_enlem,y.boylam AS ana_boylam,
                   k.enlem AS aday_enlem,k.boylam AS aday_boylam,
                   k.kaynak AS aday_kaynak
            FROM yerler y JOIN sehirler s ON s.sehir_id=y.sehir_id
            LEFT JOIN koordinat_adaylari k ON k.yer_id=y.yer_id
        ''')).mappings().all()
        lookup={int(row['yer_id']):row for row in existing}
        for r in records:
            status='ATLANDI'
            try:
                pid=int(r['yer_id'])
                d=lookup.get(pid)
                if not d:
                    status='YER_YOK'
                elif norm(r['gezilecek_yer'])=='arter' or pid==278:
                    status='ARTER_HARIC'
                elif not (num(r['isim_benzerligi']) >= .95 and num(r['koordinat_farki_metre']) <= 100):
                    status='KIMLIK_INCELEME_GEREKLI'
                elif r['kontrol_sonucu'].strip() != 'KAYNAK_KOORDINATI_ESLESIYOR':
                    status='KAYNAK_UYUMSUZ'
                elif norm(d['yer_adi'])!=norm(r['gezilecek_yer']) or norm(d['sehir'])!=norm(r['sehir']) or norm(d['ulke'])!=norm(r['ulke']):
                    status='KIMLIK_VERITABANI_UYUSMUYOR'
                else:
                    lat,lon=num(r['aday_enlem']),num(r['aday_boylam'])
                    source_lat,source_lon=num(r['kaynak_enlem']),num(r['kaynak_boylam'])
                    if not (math.isfinite(lat) and math.isfinite(lon) and -90<=lat<=90 and -180<=lon<=180):
                        status='GECERSIZ_KOORDINAT'
                    elif abs(lat-source_lat)>0.00001 or abs(lon-source_lon)>0.00001:
                        status='CSV_KAYNAK_FARKLI'
                    elif d['aday_enlem'] is None or d['aday_boylam'] is None:
                        status='ADAY_BOS'
                    elif abs(float(d['aday_enlem'])-lat)>0.000001 or abs(float(d['aday_boylam'])-lon)>0.000001:
                        status='ADAY_SONRADAN_DEGISMIS'
                    elif d['ana_enlem'] is not None or d['ana_boylam'] is not None:
                        status='ANA_TABLO_ZATEN_DOLU'
                    else:
                        status='AKTARILABILIR_KAYNAK_UYUMLU'
                        plan.append((pid,lat,lon))
            except (ValueError,TypeError,OverflowError):
                status='SAYI_VEYA_FORMAT_HATASI'
            results.append({'yer_id':r['yer_id'],'ulke':r['ulke'],'sehir':r['sehir'],'gezilecek_yer':r['gezilecek_yer'],'sonuc':status})
        print('\n--- KAYNAK UYUMLU 98 KAYIT - ON KONTROL ---')
        for k,n in sorted(Counter(x['sonuc'] for x in results).items()):
            print(f'{k}: {n}')
        print(f'\nAna tabloya eklenebilecek kaynak-uyumlu aday: {len(plan)}')
        print('UYARI: Ayni OSM kaynagi ile eslesme, bagimsiz ziyaret/giris noktasi dogrulamasi DEGILDIR.')
        print('Bu program sadece OSM isim/koordinat uyumuna dayali bir prototip aktarimidir.')
        print('Sadece kullanici kaynak ve konumu yeterli gordugunde kullanilmalidir.')
        print('Ana tabloda var olan koordinatlar korunur; aday kaynak/durum degismez.')
        if plan:
            answer=input('\nKaynak uyumlu adaylari prototip normal API icin aktaracaksan EVET yaz (aksi halde bos birak): ').strip()
            if answer=='EVET':
                for pid,lat,lon in plan:
                    rowcount=db.execute(text('''
                        UPDATE yerler y SET enlem=:lat,boylam=:lon
                        WHERE y.yer_id=:pid AND y.enlem IS NULL AND y.boylam IS NULL
                        AND EXISTS (SELECT 1 FROM koordinat_adaylari k WHERE k.yer_id=y.yer_id
                            AND ABS(k.enlem-:lat)<0.000001 AND ABS(k.boylam-:lon)<0.000001)
                    '''),{'pid':pid,'lat':lat,'lon':lon}).rowcount
                    if rowcount != 1:
                        raise RuntimeError(f'{pid}: kayit islemi sirasinda veri degisti; rollback')
                db.commit()
                for r in results:
                    if r['sonuc']=='AKTARILABILIR_KAYNAK_UYUMLU':
                        r['sonuc']='AKTARILDI_KAYNAK_UYUMLU'
                print(f'BASARILI: {len(plan)} koordinat aktarildi (bagimsiz dogrulanmis sayilmaz).')
            else:
                db.rollback()
                print('AKTARIM IPTAL: Veritabani degistirilmedi.')
        else:
            db.rollback()
            print('Aktarilacak yeni kayit yok.')
        with REPORT.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=FIELDS,delimiter=';'); w.writeheader(); w.writerows(results)
        print(f'Rapor: {REPORT}')
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == '__main__':
    main()
