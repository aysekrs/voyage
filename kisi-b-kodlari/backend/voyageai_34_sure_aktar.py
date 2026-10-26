"""VoyageAI 34 özel ziyaret süresi: önce dry-run, --apply ile onaylı aktarma."""
import argparse
import csv
from pathlib import Path
from sqlalchemy import select
from database import SessionLocal
from city_models import Yer, Sehir

DOSYA = Path(__file__).resolve().parent / 'voyageai_34_ziyaret_suresi_tahminleri.csv'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Onay vererek veritabanına kaydet')
    args = parser.parse_args()
    with DOSYA.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 34 or len({r['yer_id'] for r in rows}) != 34:
        raise ValueError('34 benzersiz yer bekleniyor; CSV dosyasini kontrol et.')
    db = SessionLocal()
    try:
        updates=[]
        for row in rows:
            yer = db.get(Yer, int(row['yer_id']))
            if yer is None:
                raise ValueError(f"Yer bulunamadi: {row['yer_id']}")
            sehir = db.get(Sehir, yer.sehir_id)
            if (yer.ad != row['yer_adi'] or sehir is None or
                sehir.ad != row['sehir'] or sehir.ulke != row['ulke']):
                raise ValueError(f"Kimlik/isim/konum eslesmedi: {row['yer_id']}")
            sure = int(row['onaylanan_sure'])
            if not 15 <= sure <= 600:
                raise ValueError(f"Supheli sure: {row['yer_id']}")
            if yer.ziyaret_suresi is None:
                updates.append((yer, sure))
            else:
                print(f"Atlandi: {yer.ad} (mevcut: {yer.ziyaret_suresi} dk)")
        print(f"Kontrol tamam: {len(rows)} satir, {len(updates)} kayit yazilabilir.")
        if not args.apply:
            print('Veritabani DEGISTIRILMEDI. Aktarmak icin --apply kullan.')
            return
        if input('Bu TAHMIN surelerini kaydetmek icin EVET yaz: ').strip() != 'EVET':
            print('Iptal edildi; veritabani degismedi.')
            return
        for yer, sure in updates:
            yer.ziyaret_suresi = sure
        db.commit()
        print(f'Basarili: {len(updates)} kayit guncellendi.')
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == '__main__':
    main()
