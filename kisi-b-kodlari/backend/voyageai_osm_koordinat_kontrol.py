r"""VoyageAI: OSM aday konumlarini uzaktaki kaynakla topluca karsilastirir.
Kullanim: backend klasorunde: .\venv\Scripts\python.exe voyageai_osm_koordinat_kontrol.py
SADECE OKUR; koordinat_dogrulandi / kayit_onayi bayraklarini degistirmez.
OSM way/relation merkezleri ziyaretci giris noktasi olmayabilir.
"""
import csv
import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from sqlalchemy import text
from database import SessionLocal

OUTPUT = Path(__file__).with_name('osm_koordinat_kontrol_sonuclari.csv')
OVERPASS = 'https://overpass.kumi.systems/api/interpreter'
SOURCE_PATTERN = re.compile(r'^https?://(?:www\.)?openstreetmap\.org/(node|way|relation)/(\d+)(?:[/?#].*)?$')


def distance_m(a, b, c, d):
    radius = 6371000.0
    dlat = math.radians(c - a)
    dlon = math.radians(d - b)
    x = math.sin(dlat/2)**2 + math.cos(math.radians(a))*math.cos(math.radians(c))*math.sin(dlon/2)**2
    return 2*radius*math.atan2(math.sqrt(x), math.sqrt(max(0.0, 1-x)))


def fetch_batch(by_type):
    parts = []
    for kind in ('node', 'way', 'relation'):
        ids = sorted(by_type[kind])
        if ids:
            parts.append(f'{kind}(id:{",".join(map(str, ids))});')
    if not parts:
        return {}
    query = '[out:json][timeout:90];(' + ''.join(parts) + ');out center tags;'
    request = urllib.request.Request(
        OVERPASS,
        data=urllib.parse.urlencode({'data': query}).encode('utf-8'),
        headers={'User-Agent':'VoyageAI-UniversityPrototype/1.0 (OSM source audit)', 'Accept':'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(request, timeout=120) as r:
        data = json.load(r)
    return {(o['type'], int(o['id'])): o for o in data.get('elements', [])}


def main():
    with SessionLocal() as db:
        records = db.execute(text('''
            SELECT id,sehir_adi,ad,osm_kaynak,enlem,boylam
            FROM yeni_yer_adaylari ORDER BY sehir_adi, id
        ''')).mappings().all()
    records = [dict(r) for r in records]
    if not records:
        print('Aday bulunamadi.'); return
    groups = {'node':set(), 'way':set(), 'relation':set()}
    for r in records:
        m = SOURCE_PATTERN.match((r['osm_kaynak'] or '').strip())
        if m:
            r['_key'] = (m.group(1), int(m.group(2)))
            groups[m.group(1)].add(int(m.group(2)))
        else:
            r['_key'] = None
    sources = {}
    try:
        print('OpenStreetMap Overpass kayitlari sorgulaniyor...')
        # Tek servis cagrisi: kotayi korur.
        sources = fetch_batch(groups)
        print('OSM kaydi donen:', len(sources))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        print('OSM baglanti hatasi:', exc)
        print('Kayitlar KONTROL_EDILEMEDI olarak raporlanacak; onay verilmeyecek.')
    results = []
    for r in records:
        src = sources.get(r['_key']) if r['_key'] else None
        status, d, osm_name = 'KONTROL_EDILEMEDI', '', ''
        osm_lat, osm_lon = '', ''
        if src:
            center = src.get('center', src)
            osm_lat, osm_lon = center.get('lat'), center.get('lon')
            osm_name = (src.get('tags') or {}).get('name', '')
            if osm_lat is not None and osm_lon is not None and r['enlem'] is not None and r['boylam'] is not None:
                d = round(distance_m(float(r['enlem']),float(r['boylam']),float(osm_lat),float(osm_lon)), 1)
                status = 'OSM_MERKEZI_ESLESIYOR' if d <= 150 else 'KOORDINAT_FARKI_INCELENECEK'
            else:
                status = 'EKSIK_KOORDINAT'
        elif r['_key'] and sources:
            status = 'OSM_KAYDI_BULUNAMADI'
        results.append({
            'aday_id':r['id'], 'sehir':r['sehir_adi'], 'ad':r['ad'],
            'osm_kaynak':r['osm_kaynak'], 'kayit_enlem':r['enlem'], 'kayit_boylam':r['boylam'],
            'osm_enlem':osm_lat, 'osm_boylam':osm_lon, 'osm_ad':osm_name,
            'fark_metre':d, 'teknik_kontrol':status,
            'not':'OSM merkezi fiziksel giris/rota baslangici dogrulamasi degildir.'
        })
    with OUTPUT.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f, fieldnames=list(results[0])); w.writeheader(); w.writerows(results)
    counts=Counter(r['teknik_kontrol'] for r in results)
    print('\nKOORDINAT KONTROL OZETI')
    for status,n in sorted(counts.items()):print(status, ':', n)
    print('Rapor:', OUTPUT)
    print('Veritabaninda HICBIR degisiklik yapilmadi; hicbir aday onaylanmadi.')

if __name__ == '__main__':
    main()
