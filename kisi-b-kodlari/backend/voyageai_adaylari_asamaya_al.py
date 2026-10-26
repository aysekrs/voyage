"""VoyageAI: import 98 UNVERIFIED candidates into a separate review table.

From backend directory (copy this file and voyageai_98_incelemeye_hazir.csv):
  .\venv\Scripts\python.exe voyageai_adaylari_asamaya_al.py
No changes to existing 'yerler' or 'sehirler' rows. Safe to re-run.
"""
import csv
from pathlib import Path
from sqlalchemy import text
from database import SessionLocal

CSV = Path(__file__).with_name('voyageai_98_incelemeye_hazir.csv')
CREATE = '''
CREATE TABLE IF NOT EXISTS yeni_yer_adaylari (
  id BIGSERIAL PRIMARY KEY,
  sehir_id INTEGER NOT NULL,
  sehir_adi TEXT NOT NULL,
  ad TEXT NOT NULL,
  kategori TEXT,
  enlem DOUBLE PRECISION,
  boylam DOUBLE PRECISION,
  osm_kaynak TEXT NOT NULL,
  durum TEXT NOT NULL DEFAULT 'inceleme_bekliyor',
  ziyaret_suresi INTEGER,
  ortalama_ucret NUMERIC(12,2),
  kayit_onayi BOOLEAN NOT NULL DEFAULT FALSE,
  koordinat_dogrulandi BOOLEAN NOT NULL DEFAULT FALSE,
  CONSTRAINT uq_osm_city UNIQUE(sehir_id, osm_kaynak),
  CONSTRAINT lat_bounds CHECK(enlem IS NULL OR enlem BETWEEN -90 AND 90),
  CONSTRAINT lon_bounds CHECK(boylam IS NULL OR boylam BETWEEN -180 AND 180)
)
'''
UPSERT = '''
INSERT INTO yeni_yer_adaylari
  (sehir_id, sehir_adi, ad, kategori, enlem, boylam, osm_kaynak, durum)
VALUES
  (:sehir_id, :sehir_adi, :ad, :kategori, :enlem, :boylam, :osm_kaynak, :durum)
ON CONFLICT (sehir_id, osm_kaynak) DO NOTHING
'''

def main():
    if not CSV.exists():
        raise SystemExit(f'CSV bulunamadi: {CSV}')
    with CSV.open(encoding='utf-8-sig',newline='') as f:
        candidates = list(csv.DictReader(f))
    if len(candidates) != 98:
        raise SystemExit(f'Beklenen 98 aday, bulunan {len(candidates)}. Dosyayi kontrol edin.')
    rows=[]
    for r in candidates:
        if not r['ad'].strip() or not r['kaynak'].startswith('https://www.openstreetmap.org/'):
            raise SystemExit('Eksik ad veya gecersiz OSM kaynagi var.')
        rows.append({
            'sehir_id':int(r['sehir_id']), 'sehir_adi':r['sehir'].strip(),
            'ad':r['ad'].strip(), 'kategori':r.get('onerilen_kategori') or r['kategori'],
            'enlem':float(r['enlem']), 'boylam':float(r['boylam']),
            'osm_kaynak':r['kaynak'], 'durum':'inceleme_bekliyor',
        })
    with SessionLocal.begin() as db:
        db.execute(text(CREATE))
        db.execute(text(UPSERT),rows)
        stats=db.execute(text('''SELECT sehir_adi, COUNT(*) AS aday
                         FROM yeni_yer_adaylari
                         GROUP BY sehir_adi ORDER BY sehir_adi''')).fetchall()
        main_count=db.execute(text('SELECT COUNT(*) FROM yerler')).scalar_one()
        print('INCELEME TABLOSU - adaylar:')
        for city,count in stats:
            print(f'  {city}: {count}')
        print('Mevcut yerler tablosu kayit sayisi:', main_count)
        print('Ana yerler tablosuna EKLEME YAPILMADI.')

if __name__=='__main__':
    main()
