"""VoyageAI: one-time OSM Nominatim candidate search for 30 missing POIs.
No database writes. Observe https://operations.osmfoundation.org/policies/nominatim/
"""
import csv
import json
import time
from pathlib import Path
from urllib.parse import urlencode
import requests

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / 'VoyageAI_30_Koordinat_Adaylari_Kontrol.csv'
OUTPUT = ROOT / 'VoyageAI_30_OSM_Koordinat_Kontrol.csv'
CACHE = ROOT / 'VoyageAI_30_OSM_Arama_Onbellek.json'
COUNTRIES = {'Avusturya':'at', 'Belçika':'be', 'Fransa':'fr', 'İspanya':'es', 'İsviçre':'ch', 'İtalya':'it', 'Mısır':'eg', 'Almanya':'de', 'Hollanda':'nl', 'Portekiz':'pt', 'Türkiye':'tr'}

if not INPUT.exists():
    raise SystemExit(f'CSV bulunamadi: {INPUT}')
with INPUT.open('r', encoding='utf-8-sig', newline='') as f:
    rows = list(csv.DictReader(f, delimiter=';'))
if not rows or 'yer_id' not in rows[0]:
    raise SystemExit('CSV okunamadi. Noktali virgul ayracini ve yer_id sutununu kontrol et.')
unique = {}
for row in rows:
    unique.setdefault(row['yer_id'], row)
rows = list(unique.values())

contact = input('Nominatim icin iletisim e-postasi (yalnizca User-Agent icinde kullanilir): ').strip()
if '@' not in contact or ' ' in contact:
    raise SystemExit('Gecerli e-posta gerekli: Nominatim istemci kimligi politikasina uyulmalidir.')
headers = {'User-Agent':f'VoyageAI-university-one-time-POI-audit/1.0 ({contact})', 'Accept-Language':'en'}
cache = json.loads(CACHE.read_text('utf-8')) if CACHE.exists() else {}
results = []
last_call = 0.0
print(f'{len(rows)} farkli yer islenecek. Veritabani degistirilmeyecek.')
for index, row in enumerate(rows, 1):
    key = row['yer_id']
    q = ', '.join(filter(None, [row.get('gezilecek_yer','').strip(), row.get('sehir','').strip(), row.get('ulke','').strip()]))
    if key in cache:
        info = cache[key]
    else:
        wait = max(0, 1.5 - (time.monotonic() - last_call))
        time.sleep(wait)
        last_call = time.monotonic()
        try:
            response = requests.get('https://nominatim.openstreetmap.org/search', params={
                'q': q, 'format':'jsonv2','limit':3,'addressdetails':1,
                **({'countrycodes':COUNTRIES[row['ulke']]} if row.get('ulke') in COUNTRIES else {})
            }, headers=headers, timeout=25)
            response.raise_for_status()
            data = response.json()
            info = {'status':'ADAY_BULUNDU' if data else 'SONUC_YOK', 'results':data}
        except requests.RequestException as e:
            print('Ag veya API hatasi:', str(e)[:160], '- islem durduruldu.')
            break
        cache[key] = info
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding='utf-8')
    options = info.get('results', [])
    for rank, place in enumerate(options, 1):
        results.append({'yer_id':key,'ulke':row.get('ulke',''),'sehir':row.get('sehir',''),
                        'gezilecek_yer':row.get('gezilecek_yer',''),'arama_metni':q,
                        'aday_sirasi':rank, 'enlem':place.get('lat',''), 'boylam':place.get('lon',''),
                        'eslesen_adres':place.get('display_name',''),'osm_tur':place.get('type',''),
                        'osm_sinif':place.get('class',''), 'durum':'INCELEME_GEREKLI',
                        'kaynak':'OpenStreetMap Nominatim'})
    if not options:
        results.append({'yer_id':key,'ulke':row.get('ulke',''),'sehir':row.get('sehir',''),
                        'gezilecek_yer':row.get('gezilecek_yer',''),'arama_metni':q,
                        'aday_sirasi':'','enlem':'','boylam':'','eslesen_adres':'','osm_tur':'',
                        'osm_sinif':'','durum':info.get('status','SONUC_YOK'),'kaynak':'OpenStreetMap Nominatim'})
    print(f'[{index}/{len(rows)}] {key}: {info.get("status")} ({len(options)} aday)')

fields = ['yer_id','ulke','sehir','gezilecek_yer','arama_metni','aday_sirasi','enlem','boylam',
          'eslesen_adres','osm_tur','osm_sinif','durum','kaynak']
with OUTPUT.open('w', encoding='utf-8-sig', newline='') as f:
    writer=csv.DictWriter(f, fieldnames=fields, delimiter=';')
    writer.writeheader()
    writer.writerows(results)
found=len({r['yer_id'] for r in results if r['enlem'] and r['boylam']})
print(f'BITTI: {found}/{len(rows)} yer icin en az bir OSM adayi. CSV: {OUTPUT}')
print('UYARI: Sonuclar dogrulanmis koordinat degildir. Kaydetmeden once tek tek yer eslesmesi kontrol edilmeli.')
print('Atif: © OpenStreetMap contributors (ODbL).')
