"""VoyageAI: Koordinat adaylarını ayrı tabloda saklar; yerler tablosuna dokunmaz.

Önizleme: python koordinat_adaylarini_kaydet.py
Yükleme:  python koordinat_adaylarini_kaydet.py --apply
"""
import argparse
import csv
import math
from collections import Counter
from pathlib import Path
from sqlalchemy import text
from database import engine

CSV_PATH = Path(__file__).resolve().parent / 'koordinat_266_ileri_denetim.csv'
KNOWN_STATES = {'ONCELIKLI_ADAY_KONTROL', 'EK_INCELEME', 'YENI_ARAMA_GEREKLI'}

def norm(v):
    return ' '.join(str(v or '').strip().casefold().split())

def coord(v, low, high):
    if v is None or not str(v).strip():
        return None
    n = float(v)
    if not math.isfinite(n) or not low <= n <= high:
        raise ValueError(f'Gecersiz koordinat: {v!r}')
    return n

def load_csv():
    if not CSV_PATH.exists():
        raise ValueError(f'Dosya bulunamadi: {CSV_PATH}')
    with CSV_PATH.open(encoding='utf-8-sig', newline='') as f:
        r = csv.DictReader(f)
        required = {'yer_id','ulke','sehir','yer_adi','aday_enlem','aday_boylam','ileri_denetim'}
        if not required.issubset(r.fieldnames or []):
            raise ValueError(f'Eksik sutunlar: {required - set(r.fieldnames or [])}')
        rows = list(r)
    if len(rows) != 266:
        raise ValueError(f'266 satir bekleniyordu, {len(rows)} geldi')
    ids = set()
    result = []
    for r in rows:
        if None in r:
            raise ValueError('CSV satirinda fazla alan var')
        i = int(r['yer_id'])
        if i in ids:
            raise ValueError(f'Tekrarli ID: {i}')
        ids.add(i)
        lat, lon = coord(r['aday_enlem'],-90,90),coord(r['aday_boylam'],-180,180)
        if (lat is None) != (lon is None):
            raise ValueError(f'Yalnizca tek koordinat var: {i}')
        state = r['ileri_denetim'].strip()
        if state not in KNOWN_STATES:
            raise ValueError(f'Beklenmeyen inceleme durumu: {i} {state}')
        if state == 'YENI_ARAMA_GEREKLI' and lat is not None:
            raise ValueError(f'Yeni arama durumunda koordinat var: {i}')
        if state != 'YENI_ARAMA_GEREKLI' and lat is None:
            raise ValueError(f'Aday durumunda koordinat eksik: {i}')
        result.append(dict(yer_id=i, ulke=r['ulke'].strip(), sehir=r['sehir'].strip(),
                           yer_adi=r['yer_adi'].strip(), enlem=lat, boylam=lon,
                           durum=state, kaynak='Geoapify - otomatik aday'))
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    rows = load_csv()
    print('Kayit sayisi:', len(rows))
    print('Durumlar:', dict(Counter(r['durum'] for r in rows)))
    with engine.connect() as c:
        # Mevcut yerlerin adlarını ve şehir/ülkesini kimlik bazında karşılaştır.
        existing = c.execute(text('''
            SELECT y.yer_id, y.ad AS yer_adi, s.ad AS sehir, s.ulke
            FROM yerler y JOIN sehirler s ON s.sehir_id = y.sehir_id
        ''')).mappings().all()
        by_id = {r['yer_id']: r for r in existing}
        for r in rows:
            old = by_id.get(r['yer_id'])
            if old is None or any(norm(old[k]) != norm(r[k]) for k in ('ulke','sehir','yer_adi')):
                raise ValueError(f'Kimlik/isim/sehir/ulke eslesmedi: yer_id={r["yer_id"]}')
    print('Kimlik ve isim eslesmeleri basarili.')
    if not args.apply:
        print('ONIZLEME: Veritabani DEGISTIRILMEDI. Yuklemek icin --apply kullan.')
        return
    if input('Adaylari AYRI TABLOYA kaydetmek icin EVET yaz: ').strip() != 'EVET':
        print('Iptal edildi.')
        return
    with engine.begin() as c:
        c.execute(text('''
            CREATE TABLE IF NOT EXISTS koordinat_adaylari (
                yer_id INTEGER PRIMARY KEY REFERENCES yerler(yer_id),
                enlem DOUBLE PRECISION,
                boylam DOUBLE PRECISION,
                durum VARCHAR(50) NOT NULL,
                kaynak VARCHAR(100) NOT NULL,
                guncelleme_zamani TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CHECK ((enlem IS NULL AND boylam IS NULL)
                       OR (enlem BETWEEN -90 AND 90 AND boylam BETWEEN -180 AND 180))
            )
        '''))
        # Bu çalıştırmaya ait kayıtları ekle/güncelle; yerler tablosu değişmez.
        for r in rows:
            c.execute(text('''
                INSERT INTO koordinat_adaylari (yer_id,enlem,boylam,durum,kaynak)
                VALUES (:yer_id,:enlem,:boylam,:durum,:kaynak)
                ON CONFLICT (yer_id) DO UPDATE SET
                    enlem=EXCLUDED.enlem, boylam=EXCLUDED.boylam,
                    durum=EXCLUDED.durum, kaynak=EXCLUDED.kaynak,
                    guncelleme_zamani=NOW()
            '''), r)
    print('Basarili: 266 aday kaydi AYRI TABLOYA kaydedildi.')
    print('yerler.enlem ve yerler.boylam DEGISTIRILMEDI.')

if __name__ == '__main__':
    main()
