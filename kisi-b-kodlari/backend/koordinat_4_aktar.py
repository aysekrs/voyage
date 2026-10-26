import argparse
import csv
from pathlib import Path

from sqlalchemy import select
from database import SessionLocal
from city_models import Sehir, Yer

CSV_PATH = Path(__file__).resolve().parent / 'voyageai_ilk_4_koordinat_kontrol.csv'
REQUIRED = {'ulke', 'sehir', 'ad', 'harita_kontrolu', 'onayli_enlem', 'onayli_boylam'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Onayla ve kaydet')
    args = parser.parse_args()

    with CSV_PATH.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if not REQUIRED.issubset(set(reader.fieldnames or [])):
            raise ValueError('CSV sutunlari eksik: ' + str(REQUIRED - set(reader.fieldnames or [])))
        rows = list(reader)

    if len(rows) != 4:
        raise ValueError(f'Tam 4 satir bekleniyor, gelen: {len(rows)}')

    seen = set()
    for row in rows:
        key = (row['ulke'].strip(), row['sehir'].strip(), row['ad'].strip())
        if key in seen:
            raise ValueError('Tekrar eden kayit: ' + str(key))
        seen.add(key)
        if row['harita_kontrolu'].strip().upper() != 'ONAYLANDI':
            raise ValueError('Onaylanmamis kayit: ' + str(key))
        lat, lon = float(row['onayli_enlem']), float(row['onayli_boylam'])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError('Gecersiz koordinat: ' + str(key))

    db = SessionLocal()
    try:
        changes = []
        for row in rows:
            matches = db.execute(
                select(Yer).join(Sehir, Yer.sehir_id == Sehir.sehir_id).where(
                    Sehir.ulke == row['ulke'].strip(),
                    Sehir.ad == row['sehir'].strip(),
                    Yer.ad == row['ad'].strip(),
                )
            ).scalars().all()
            if len(matches) != 1:
                raise ValueError(f"Tek eslesme bulunamadi ({len(matches)}): {row['ulke']} / {row['sehir']} / {row['ad']}")
            place = matches[0]
            if place.enlem is not None or place.boylam is not None:
                raise ValueError(f'Mevcut koordinat var; uzerine yazilmadi: {place.yer_id} {place.ad}')
            lat, lon = float(row['onayli_enlem']), float(row['onayli_boylam'])
            changes.append((place, lat, lon))
            print(f'HAZIR: yer_id={place.yer_id}, {row["sehir"]} / {place.ad} -> {lat}, {lon}')

        print(f'Kontrol tamam: {len(changes)} kayit uygun.')
        if not args.apply:
            print('VERITABANI DEGISTIRILMEDI. Aktarmak icin --apply kullan.')
            return

        confirm = input('4 koordinati kaydetmek icin EVET yaz: ').strip()
        if confirm != 'EVET':
            print('Iptal edildi. Veri degismedi.')
            return

        for place, lat, lon in changes:
            place.enlem, place.boylam = lat, lon
        db.commit()
        print(f'Basarili: {len(changes)} kayit guncellendi.')
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == '__main__':
    main()
