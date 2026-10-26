"""VoyageAI: Geoapify ile koordinat adayı çıkarma.

Kullanım: backend/.env içine GEOAPIFY_API_KEY=... koyun.
        python -m pip install requests python-dotenv
        python koordinat_toplu.py
        python koordinat_toplu.py --limit 10

Veritabanına dokunmaz. Güvenli görünen eşleşmeler otomatik olarak
'koordinat_guvenli_adaylar.csv' dosyasına, şüpheliler ayrı dosyaya yazılır.
"""
import argparse
import csv
import os
import re
import time
import unicodedata
from pathlib import Path
from difflib import SequenceMatcher

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'eksik_koordinatlar.csv'
OUTPUT = ROOT / 'koordinat_sonuclari.csv'
SAFE = ROOT / 'koordinat_guvenli_adaylar.csv'
REVIEW = ROOT / 'koordinat_incelenecek.csv'
API = 'https://api.geoapify.com/v1/geocode/search'

COUNTRIES = {'Türkiye': 'tr', 'Fransa': 'fr', 'İtalya': 'it', 'Almanya': 'de',
             'Belçika': 'be', 'Hollanda': 'nl', 'İsviçre': 'ch', 'Portekiz': 'pt',
             'İspanya': 'es', 'Mısır': 'eg', 'Avusturya': 'at'}

ALIASES = {'Berlin Duvarı Anıtı': 'Berlin Wall Memorial', 'Brandenburg Kapısı': 'Brandenburg Gate',
           'Müze Adası': 'Museum Island', 'Reichstag Binası': 'Reichstag Building',
           'Ayasofya': 'Hagia Sophia', 'Sultanahmet Camii': 'Blue Mosque',
           'Galata Kulesi': 'Galata Tower', 'Topkapı Sarayı': 'Topkapi Palace',
           'Gülhane Parkı': 'Gulhane Park', 'Frauenkirche': 'Frauenkirche Dresden'}

FIELDS = ['ulke', 'sehir', 'ad', 'enlem', 'boylam', 'bulunan_adres',
          'eslesme_durumu', 'guven_puani', 'kaynak']


def norm(s):
    s = unicodedata.normalize('NFKD', (s or '').casefold())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def similarity(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0
    if a in b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def request_geo(session, row, key):
    country = COUNTRIES.get(row['ulke'], '')
    name = ALIASES.get(row['ad'], row['ad'])
    query = f"{name}, {row['sehir']}, {row['ulke']}"
    resp = session.get(API, params={'text': query, 'format': 'json',
                                    'filter': f'countrycode:{country}' if country else None,
                                    'limit': 5, 'apiKey': key}, timeout=25)
    if resp.status_code in (401, 403):
        raise RuntimeError('API anahtarı geçersiz veya yetki yok. .env dosyasını kontrol et.')
    if resp.status_code == 429:
        raise RuntimeError('API kota / hız sınırı doldu. Daha sonra yeniden çalıştır.')
    resp.raise_for_status()
    candidates = resp.json().get('results', [])
    if not candidates:
        return None
    scored = []
    for item in candidates:
        place_labels = ' '.join(str(item.get(k) or '') for k in
                                ('name', 'address_line1', 'formatted', 'street'))
        name_score = max(similarity(row['ad'], place_labels), similarity(name, place_labels))
        city_string = ' '.join(str(item.get(k) or '') for k in
                               ('city', 'town', 'village', 'suburb', 'county', 'formatted'))
        city_match = norm(row['sehir']) in norm(city_string)
        country_match = item.get('country_code', '').lower() == country
        quality = float(item.get('rank', {}).get('confidence', 0) or 0)
        score = round(100 * (0.65 * name_score + 0.25 * (1 if city_match else 0) + 0.10 * quality), 1)
        scored.append((score, name_score, city_match, country_match, item))
    scored.sort(key=lambda a: a[0], reverse=True)
    score, name_score, city_match, country_match, item = scored[0]
    # Bilerek çok katı: kabul bile otomatik doğrulama değil, sadece güçlü aday.
    status = 'GUCLU_ADAY' if score >= 90 and name_score >= .94 and city_match and country_match else 'INCELE'
    return {'lat': item.get('lat'), 'lon': item.get('lon'),
            'address': item.get('formatted', ''), 'status': status, 'score': score}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=0, help='Test için en fazla N sorgu')
    args = parser.parse_args()
    load_dotenv(ROOT / '.env')
    key = os.getenv('GEOAPIFY_API_KEY', '').strip()
    if not key:
        raise SystemExit('Önce backend/.env dosyasına GEOAPIFY_API_KEY=anahtar ekle.')
    if not SOURCE.exists():
        raise SystemExit('eksik_koordinatlar.csv dosyası backend içinde bulunamadı.')
    with SOURCE.open(encoding='utf-8-sig', newline='') as f:
        entries = list(csv.DictReader(f))
    if args.limit > 0:
        entries = entries[:args.limit]
    all_rows = []
    with requests.Session() as session:
        for i, row in enumerate(entries, 1):
            record = {'ulke': row['ulke'], 'sehir': row['sehir'], 'ad': row['ad'],
                      'enlem': '', 'boylam': '', 'bulunan_adres': '',
                      'eslesme_durumu': 'BULUNAMADI', 'guven_puani': '', 'kaynak': 'Geoapify'}
            try:
                hit = request_geo(session, row, key)
                if hit and hit['lat'] is not None and hit['lon'] is not None:
                    record.update(enlem=hit['lat'], boylam=hit['lon'],
                                  bulunan_adres=hit['address'], eslesme_durumu=hit['status'],
                                  guven_puani=hit['score'])
            except requests.RequestException as exc:
                record['eslesme_durumu'] = 'HATA'
                record['bulunan_adres'] = str(exc)[:160]
            all_rows.append(record)
            print(f"{i}/{len(entries)} {record['ad']}: {record['eslesme_durumu']}")
            time.sleep(0.5)
    for path, rows in [(OUTPUT, all_rows),
                       (SAFE, [r for r in all_rows if r['eslesme_durumu'] == 'GUCLU_ADAY']),
                       (REVIEW, [r for r in all_rows if r['eslesme_durumu'] != 'GUCLU_ADAY'])]:
        with path.open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
    print(f"Bitti. Güçlü aday: {sum(r['eslesme_durumu']=='GUCLU_ADAY' for r in all_rows)}; "
          f"inceleme gerektiren: {sum(r['eslesme_durumu']!='GUCLU_ADAY' for r in all_rows)}")
    print('Bu dosyalar VERİTABANINI değiştirmedi. Güçlü adaylar bile kesin doğrulanmış sayılmaz.')


if __name__ == '__main__':
    main()
