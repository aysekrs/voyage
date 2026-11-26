"""VoyageAI: ana/aday koordinatı olmayan yerler için Geoapify aday CSV'si oluşturur.
Veritabanında hiçbir değişiklik yapmaz. Anahtar env GEOAPIFY_API_KEY'den veya gizli istemden alınır.
"""
import csv
import getpass
import os
import time
from pathlib import Path

import requests
from sqlalchemy import text
from database import SessionLocal

ULKE_KODLARI = {
    'Almanya': 'de', 'Avusturya': 'at', 'Belçika': 'be',
    'Fransa': 'fr', 'Hollanda': 'nl', 'İspanya': 'es',
    'İsviçre': 'ch', 'İtalya': 'it', 'Mısır': 'eg',
    'Portekiz': 'pt', 'Türkiye': 'tr'
}

SQL = text("""
SELECT y.yer_id, s.ulke, s.ad AS sehir, y.ad AS gezilecek_yer
FROM yerler y
JOIN sehirler s ON s.sehir_id = y.sehir_id
WHERE NOT COALESCE(
    y.enlem BETWEEN -90 AND 90 AND y.boylam BETWEEN -180 AND 180,
    FALSE
)
AND NOT EXISTS (
    SELECT 1 FROM koordinat_adaylari k
    WHERE k.yer_id = y.yer_id
      AND k.enlem BETWEEN -90 AND 90 AND k.boylam BETWEEN -180 AND 180
)
ORDER BY s.ulke, s.ad, y.ad
""")


def main():
    api_key = os.getenv('GEOAPIFY_API_KEY', '').strip()
    if not api_key:
        api_key = getpass.getpass('Geoapify API anahtari (ekranda gorunmez): ').strip()
    if not api_key:
        print('API anahtari verilmedi, islem durduruldu.')
        return

    with SessionLocal() as db:
        kayitlar = db.execute(SQL).mappings().all()
    if not kayitlar:
        print('Eksik koordinat adayi olan yer bulunamadi.')
        return

    cikti = Path(__file__).resolve().parent / 'VoyageAI_30_Koordinat_Adaylari_Kontrol.csv'
    sutunlar = ['yer_id', 'ulke', 'sehir', 'gezilecek_yer', 'arama_metni',
                'aday_sirasi', 'enlem', 'boylam', 'eslesen_adres', 'sonuc_adi',
                'confidence', 'confidence_city_level', 'durum']
    basarili, bos, hatali = 0, 0, 0
    with cikti.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=sutunlar, delimiter=';')
        writer.writeheader()
        for i, kayit in enumerate(kayitlar, start=1):
            k = dict(kayit)
            arama = f"{k['gezilecek_yer']}, {k['sehir']}, {k['ulke']}"
            temel = {**k, 'arama_metni': arama}
            print(f"[{i}/{len(kayitlar)}] {arama}")
            try:
                params = {'text': arama, 'format': 'json', 'limit': 3, 'apiKey': api_key}
                country = ULKE_KODLARI.get(k['ulke'])
                if country:
                    params['filter'] = f'countrycode:{country}'
                cevap = requests.get('https://api.geoapify.com/v1/geocode/search',
                                     params=params, timeout=25)
                cevap.raise_for_status()
                results = cevap.json().get('results', [])
                if not results:
                    writer.writerow({**temel, 'durum': 'SONUC_YOK'})
                    bos += 1
                else:
                    basarili += 1
                    for rank, r in enumerate(results, start=1):
                        writer.writerow({
                            **temel,
                            'aday_sirasi': rank,
                            'enlem': r.get('lat', ''),
                            'boylam': r.get('lon', ''),
                            'eslesen_adres': r.get('formatted', ''),
                            'sonuc_adi': r.get('name', ''),
                            'confidence': r.get('rank', {}).get('confidence', ''),
                            'confidence_city_level': r.get('rank', {}).get('confidence_city_level', ''),
                            'durum': 'MANUEL_DOGRULAMA_GEREKLI'
                        })
            except (requests.RequestException, ValueError) as exc:
                # Anahtar veya istek ayrintilarini CSV'ye yazmayiz.
                writer.writerow({**temel, 'durum': f'API_HATASI_{getattr(getattr(exc, "response", None), "status_code", "BAGLANTI")}'})
                print('  Uyari: API istegi basarisiz; anahtar/limit/baglanti kontrol edilmeli.')
                hatali += 1
                if getattr(getattr(exc, 'response', None), 'status_code', None) in (401, 403, 429):
                    print('  Kimlik dogrulama veya kota hatasi, burada durduruluyor.')
                    break
            f.flush()
            time.sleep(0.3)
    print(f'\nCSV: {cikti}\nEn az bir sonuc: {basarili}, sonuc yok: {bos}, API hatasi: {hatali}')
    print('UYARI: Bunlar SADECE adaydir. Adresin sehir merkezi degil, ilgili ziyaret noktasi oldugunu dogrulamadan ana tabloya aktarmayin.')
    print('Veritabani degistirilmedi.')


if __name__ == '__main__':
    main()
