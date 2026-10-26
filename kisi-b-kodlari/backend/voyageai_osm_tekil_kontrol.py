"""VoyageAI: OSM aday koordinatlarını ayrı ayrı kontrol et; veritabanını değiştirmez."""
import csv
import json
import math
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from sqlalchemy import text
from database import SessionLocal

OUTPUT = Path(__file__).with_name('osm_tekil_kontrol_sonuclari.csv')
OSM_RE = re.compile(r'https?://(?:www\.)?openstreetmap\.org/(node|way|relation)/(\d+)(?:[/?#].*)?$', re.I)
HEADERS = {'User-Agent': 'VoyageAI-Student-OSM-check/1.0 (educational data validation)', 'Accept': 'application/json'}

def haversine(a, b, c, d):
    radius = 6371000.0
    p1, p2 = math.radians(a), math.radians(c)
    dp, dl = p2 - p1, math.radians(d - b)
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(x), math.sqrt(max(0, 1 - x)))

def indir(kaynak_turu, osm_id):
    ek = '' if kaynak_turu == 'node' else '/full'
    url = f'https://api.openstreetmap.org/api/0.6/{kaynak_turu}/{osm_id}{ek}.json'
    for deneme in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=35) as response:
                return json.load(response), ''
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            if isinstance(exc, urllib.error.HTTPError) and exc.code in (400, 403, 404, 410):
                return None, f'HTTP {exc.code}'
            if deneme == 2:
                return None, str(exc)[:150]
            time.sleep(2 * (deneme + 1))
    return None, 'Bilinmeyen hata'

def koordinat_bul(veri, kaynak_turu, osm_id):
    elements = veri.get('elements', [])
    asil = next((e for e in elements if e.get('type') == kaynak_turu and str(e.get('id')) == osm_id), None)
    if not asil:
        return None, None, 'Kaynak nesne bulunamadi'
    if kaynak_turu == 'node':
        return asil.get('lat'), asil.get('lon'), 'OSM node konumu'
    # Way/relation icin full yanitindaki dugumlerin sinir kutusu merkezini kullaniriz.
    # Bu yaklasim Overpass center ile bire bir ayni olmayabilir.
    dugumler = {e['id']: e for e in elements if e.get('type') == 'node' and 'lat' in e and 'lon' in e}
    if kaynak_turu == 'way':
        node_ids = asil.get('nodes', [])
    else:
        wayler = {e['id']: e for e in elements if e.get('type') == 'way'}
        node_ids = []
        for m in asil.get('members', []):
            if m.get('type') == 'node':
                node_ids.append(m.get('ref'))
            elif m.get('type') == 'way':
                node_ids.extend(wayler.get(m.get('ref'), {}).get('nodes', []))
    points = [dugumler[i] for i in node_ids if i in dugumler]
    if not points:
        return None, None, 'Geometri dugumleri bulunamadi'
    return ((min(p['lat'] for p in points) + max(p['lat'] for p in points)) / 2,
            (min(p['lon'] for p in points) + max(p['lon'] for p in points)) / 2,
            'OSM geometri sinir kutusu merkezi')

def main():
    db = SessionLocal()
    try:
        satirlar = db.execute(text('''
            SELECT id, sehir_adi, ad, enlem, boylam, osm_kaynak
            FROM yeni_yer_adaylari ORDER BY id
        ''')).mappings().all()
    finally:
        db.close()

    alanlar = ['id', 'sehir', 'ad', 'osm_kaynak', 'csv_enlem', 'csv_boylam',
              'osm_enlem', 'osm_boylam', 'fark_metre', 'kontrol_sonucu', 'konum_tipi', 'aciklama']
    sayac = {}
    with OUTPUT.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=alanlar)
        writer.writeheader()
        for index, s in enumerate(satirlar, 1):
            row = {'id': s['id'], 'sehir': s['sehir_adi'], 'ad': s['ad'], 'osm_kaynak': s['osm_kaynak'],
                   'csv_enlem': s['enlem'], 'csv_boylam': s['boylam'],
                   'osm_enlem': '', 'osm_boylam': '', 'fark_metre': '',
                   'kontrol_sonucu': 'KONTROL_EDILEMEDI', 'konum_tipi': '', 'aciklama': ''}
            match = OSM_RE.match((s['osm_kaynak'] or '').strip())
            if not match:
                row['aciklama'] = 'OSM kaynak URL formati gecersiz'
            else:
                tur, osm_id = match.groups()
                veri, hata = indir(tur.lower(), osm_id)
                if hata:
                    row['aciklama'] = hata
                else:
                    lat, lon, tur_aciklama = koordinat_bul(veri, tur.lower(), osm_id)
                    row['konum_tipi'] = tur_aciklama
                    if lat is None or lon is None or s['enlem'] is None or s['boylam'] is None:
                        row['aciklama'] = 'Karsilastirilacak koordinat eksik'
                    else:
                        fark = haversine(float(s['enlem']), float(s['boylam']), float(lat), float(lon))
                        row.update(osm_enlem=lat, osm_boylam=lon, fark_metre=round(fark, 1))
                        row['kontrol_sonucu'] = 'ESLESTI' if fark <= 150 else 'FARK_VAR'
                        row['aciklama'] = ('OSM nesne konumuyla teknik eslesme; ziyaretci girisi dogrulanmadi'
                                           if fark <= 150 else '150 metreden fazla fark: elle incele')
            writer.writerow(row)
            f.flush()
            sayac[row['kontrol_sonucu']] = sayac.get(row['kontrol_sonucu'], 0) + 1
            print(f"{index}/{len(satirlar)} | {s['ad'][:35]} | {row['kontrol_sonucu']}", flush=True)
            time.sleep(0.5)
    print('\nSONUC:', sayac)
    print('CSV:', OUTPUT)
    print('VERITABANI DEGISTIRILMEDI; KAYITLARA ONAY VERILMEDI.')

if __name__ == '__main__':
    main()
