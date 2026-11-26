"""VoyageAI: one-time alternative-name POI search (Nominatim, OSM).
Reads existing 30-place semicolon CSV; writes a new review CSV. No database changes.
Requests are sequential, >1s apart and stop on HTTP/API errors.
"""
import csv
import time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / 'VoyageAI_30_Koordinat_Adaylari_Kontrol.csv'
OUTPUT = ROOT / 'VoyageAI_30_OSM_Alternatif_Ad_Kontrol.csv'
# Grounded commonly used international names; user should review each candidate.
ALIASES = {
    271: 'Hallstatt Old Town',
    268: 'Bergisel Ski Jump Innsbruck',
    120: 'Antwerpen Centraal railway station',
    110: 'Markt Brugge',
    104: 'Galeries Royales Saint-Hubert Brussels',
    48: 'Parc national des Calanques Marseille',
    38: 'Palace of Versailles',
    39: 'Gardens of Versailles',
    207: 'Barri Gotic Barcelona',
    219: 'Alhambra Granada',
    223: 'Mercado Central Valencia',
    170: 'Lake Geneva Geneva',
    172: 'The Olympic Museum Lausanne',
    159: 'Verkehrshaus der Schweiz Luzern',
    151: 'Lake Zurich Zurich',
    60: 'Cattedrale di Santa Maria del Fiore Firenze',
    71: 'Centro Storico Napoli',
    73: 'Parco archeologico di Pompei',
    64: 'Palazzo Ducale Venezia',
    248: 'Aswan Botanical Garden',
    238: 'Red Pyramid Dahshur',
    249: 'Abu Simbel Temples',
    236: 'Grand Egyptian Museum Giza',
    235: 'Great Sphinx of Giza',
    229: 'Al-Azhar Mosque Cairo',
    231: 'Al-Azhar Park Cairo',
    232: 'Coptic Cairo',
    233: 'Nile Corniche Cairo',
    237: 'Pyramid of Djoser Saqqara',
    250: 'Ras Mohammed National Park',
}
COUNTRY_CODES = {
    'Avusturya': 'at', 'Belçika':'be', 'Fransa':'fr', 'İspanya':'es',
    'İsviçre':'ch', 'İtalya':'it', 'Mısır':'eg'
}
if not INPUT.exists():
    raise SystemExit(f'Eksik CSV: {INPUT}')
with INPUT.open('r', encoding='utf-8-sig', newline='') as f:
    original = list(csv.DictReader(f, delimiter=';'))
by_id = {}
for row in original:
    by_id.setdefault(int(row['yer_id']), row)
if len(by_id) != 30:
    raise SystemExit(f'Beklenen 30 farkli yer, bulunan {len(by_id)}. Islem durduruldu.')
contact = input('OSM icin iletisim e-postasi (yalnizca User-Agent icinde): ').strip()
if '@' not in contact or ' ' in contact:
    raise SystemExit('Gecerli e-posta gerekli.')
headers = {
    'User-Agent': f'VoyageAI-student-one-time-place-audit/1.0 ({contact})',
    'Accept-Language': 'en'
}
columns = ['yer_id','ulke','sehir','gezilecek_yer','alternatif_ad','arama_metni','aday_sirasi',
           'enlem','boylam','eslesen_adres','osm_tur','osm_sinif','durum','kaynak']
results = []
last_request_at = 0.0
print(f'{len(by_id)} yer alternatif adla aranacak. Ana veritabani degistirilmeyecek.')
try:
    for idx,(place_id,row) in enumerate(by_id.items(), 1):
        alternative = ALIASES.get(place_id)
        if not alternative:
            raise SystemExit(f'Alternatif ad eksik: {place_id}')
        q = alternative
        params = {'q':q, 'format':'jsonv2', 'limit':3, 'addressdetails':1}
        country_code = COUNTRY_CODES.get(row['ulke'])
        if country_code:
            params['countrycodes'] = country_code
        time.sleep(max(0.0, 1.6 - (time.monotonic() - last_request_at)))
        last_request_at = time.monotonic()
        response = requests.get('https://nominatim.openstreetmap.org/search',
                                params=params, headers=headers, timeout=25)
        response.raise_for_status()
        candidates = response.json()
        if not isinstance(candidates, list):
            raise RuntimeError('API beklenmedik veri dondurdu')
        base = {key:row.get(key,'') for key in ('yer_id','ulke','sehir','gezilecek_yer')}
        base.update({'alternatif_ad':alternative, 'arama_metni':q,
                     'kaynak':'OpenStreetMap Nominatim'})
        if candidates:
            for rank, item in enumerate(candidates,1):
                results.append({**base, 'aday_sirasi':rank, 'enlem':item.get('lat',''),
                    'boylam':item.get('lon',''), 'eslesen_adres':item.get('display_name',''),
                    'osm_tur':item.get('type',''), 'osm_sinif':item.get('class',''),
                    'durum':'INCELEME_GEREKLI'})
        else:
            results.append({**base,'aday_sirasi':'','enlem':'','boylam':'',
                'eslesen_adres':'','osm_tur':'','osm_sinif':'','durum':'SONUC_YOK'})
        print(f'[{idx}/30] {place_id} {alternative}: {len(candidates)} aday')
except (requests.RequestException,RuntimeError) as exc:
    print(f'ARAMA DURDU: {type(exc).__name__}: {str(exc)[:160]}')
finally:
    with OUTPUT.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns, delimiter=';')
        writer.writeheader()
        writer.writerows(results)
    count = len({r['yer_id'] for r in results if r['enlem'] and r['boylam']})
    print(f'BITTI: {count}/30 yer icin koordinat adayi bulundu. CSV: {OUTPUT}')
    print('DIKKAT: Sonuclar konum dogrulamasi degildir. Genis park/gol/sehir alanlarinda tek nokta temsili olabilir.')
    print('Kaynak: © OpenStreetMap contributors (ODbL).')
