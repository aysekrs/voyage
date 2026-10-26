"""OSM CSV teknik eşleşmelerini aday tablosunda ayrıca kaydeder.
Ana 'yerler' tablosuna ve onay bayraklarına DOKUNMAZ.
Kullanım: python voyageai_osm_sonucunu_kaydet.py
"""
import csv
from pathlib import Path
from sqlalchemy import text
from database import SessionLocal

CSV_PATH = Path(__file__).resolve().parent / 'osm_tekil_kontrol_sonuclari.csv'

def main():
    with CSV_PATH.open('r', encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise RuntimeError('CSV bos.')
    ids = [int(r['id']) for r in rows]
    if len(ids) != len(set(ids)):
        raise RuntimeError('CSV icinde yinelenen ID var.')
    for r in rows:
        if r['kontrol_sonucu'] != 'ESLESTI' or float(r['fark_metre']) > 150:
            raise RuntimeError(f"Eslestirilmemis satir: {r['id']}")

    db = SessionLocal()
    try:
        # Her CSV satırı aynı aday kaydını ve aynı OSM kaynağını göstermeli.
        for r in rows:
            sonuc = db.execute(text('''
                SELECT id, osm_kaynak, enlem, boylam
                FROM yeni_yer_adaylari WHERE id = :id
            '''), {'id': int(r['id'])}).mappings().one_or_none()
            if not sonuc:
                raise RuntimeError(f"Aday ID yok: {r['id']}")
            if sonuc['osm_kaynak'] != r['osm_kaynak']:
                raise RuntimeError(f"OSM kaynak farkli: ID {r['id']}")
            if sonuc['enlem'] is None or sonuc['boylam'] is None:
                raise RuntimeError(f"Aday koordinati bos: ID {r['id']}")
            if abs(float(sonuc['enlem']) - float(r['csv_enlem'])) > 0.000001 or abs(float(sonuc['boylam']) - float(r['csv_boylam'])) > 0.000001:
                raise RuntimeError(f"CSV ile aday koordinati farkli: ID {r['id']}")

        # Eski 'koordinat_dogrulandi' veya 'kayit_onayi' sütunlarını değiştirme.
        db.execute(text('''
            ALTER TABLE yeni_yer_adaylari
            ADD COLUMN IF NOT EXISTS osm_teknik_eslesme boolean DEFAULT false
        '''))
        db.execute(text('''
            ALTER TABLE yeni_yer_adaylari
            ADD COLUMN IF NOT EXISTS osm_kontrol_tarihi timestamp
        '''))
        for r in rows:
            db.execute(text('''
                UPDATE yeni_yer_adaylari
                   SET osm_teknik_eslesme = true,
                       osm_kontrol_tarihi = CURRENT_TIMESTAMP
                 WHERE id = :id AND osm_kaynak = :source
            '''), {'id': int(r['id']), 'source': r['osm_kaynak']})
        db.commit()
        print(f"BASARILI: {len(rows)} aday icin OSM teknik eslesme kaydedildi.")
        print("'yerler', 'kayit_onayi', 'koordinat_dogrulandi' DEGISMEDI.")
        print('Bu islem ziyaretci girisi veya fiyat dogrulamasi DEGILDIR.')
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == '__main__':
    main()
