"""VoyageAI 2. hafta: mevcut PostgreSQL verisini salt okunur biçimde denetler.
Kullanım: backend klasöründe python voyageai_toplu_veri_denetimi.py
Hiçbir tabloya INSERT/UPDATE/DELETE yapmaz.
"""
import csv
from collections import Counter
from datetime import date
from pathlib import Path
from sqlalchemy import text
from database import SessionLocal

ROOT = Path(__file__).resolve().parent
TODAY = date.today().isoformat()
# Yalnızca güncel kurumsal kaynaklardan teyit edilen ad/ziyaret erişimi.
# Bu kanıt, giriş koordinatını, ücretleri veya tüm kayıt kalitesini doğrulamaz.
SOURCES = {
    (1, 'Miniatürk Müzesi'): 'https://www.miniaturk.com.tr/Home/Ziyaret',
    (39, 'Houseboat Museum'): 'https://houseboatmuseum.nl/visit/',
    (24, 'Stasimuseum'): 'https://www.visitberlin.de/en/stasi-museum',
    (24, 'Stasi Museum'): 'https://www.visitberlin.de/en/stasi-museum',
    (8, 'Musée des Arts et Métiers'): 'https://www.arts-et-metiers.net/musee/horaires-et-acces',
    (82, 'Spanische Hofreitschule'): 'https://www.srs.at/en/visitor-information/vienna/opening-hours',
}
CITIES = (1, 8, 24, 39, 82)
with SessionLocal() as db:
    rows = db.execute(text('''
        SELECT s.ad AS sehir, y.sehir_id, y.yer_id, y.ad, y.kategori,
               y.enlem, y.boylam, y.ziyaret_suresi, y.ortalama_ucret,
               y.veri_durumu, y.kaynak_aday_id,
               a.osm_kaynak, a.osm_teknik_eslesme, a.kayit_onayi,
               a.koordinat_dogrulandi, a.ziyaret_suresi_turu,
               a.manuel_inceleme_gerekli
        FROM yerler y
        JOIN sehirler s ON s.sehir_id = y.sehir_id
        LEFT JOIN yeni_yer_adaylari a ON a.id = y.kaynak_aday_id
        WHERE y.sehir_id IN (1, 8, 24, 39, 82)
        ORDER BY s.ad, y.ad
    ''')).mappings().all()

report = []
for r in rows:
    city_id = r['sehir_id']
    name = r['ad']
    official = SOURCES.get((city_id, name), '')
    temporary = r['veri_durumu'] in ('aday', 'ozel_inceleme')
    flags = []
    if temporary: flags.append('GEÇİCİ - ziyaret uygunluğu onaysız')
    if r['enlem'] is None or r['boylam'] is None: flags.append('Giriş koordinatı yok')
    if r['ortalama_ucret'] is None: flags.append('Ücret bilinmiyor')
    if r['ziyaret_suresi'] is None: flags.append('Süre eksik')
    if r['ziyaret_suresi_turu'] == 'tahmini': flags.append('Süre tahmini')
    if r['manuel_inceleme_gerekli']: flags.append('Özel inceleme')
    report.append({
        'sehir_id': city_id, 'sehir': r['sehir'], 'yer_id': r['yer_id'], 'ad': name,
        'kategori': r['kategori'], 'veri_durumu': r['veri_durumu'] or 'önceki_kayıt',
        'kaynak_aday_id': r['kaynak_aday_id'] or '',
        'kayit_onayi': r['kayit_onayi'] if r['kayit_onayi'] is not None else '',
        'koordinat_dogrulandi': r['koordinat_dogrulandi'] if r['koordinat_dogrulandi'] is not None else '',
        'osm_teknik_eslesme': r['osm_teknik_eslesme'] if r['osm_teknik_eslesme'] is not None else '',
        'ziyaret_suresi_dk': r['ziyaret_suresi'] or '',
        'ortalama_ucret': r['ortalama_ucret'] if r['ortalama_ucret'] is not None else '',
        'osm_kaynak': r['osm_kaynak'] or '',
        'resmi_ziyaret_kaynagi': official,
        'resmi_kaynagin_kapsami': 'yer ve ziyaret bilgisi; giriş noktası değil' if official else '',
        'kontrol_tarihi': TODAY if official else '',
        'eksik_kontroller': '; '.join(flags) or 'Bu denetimle ek eksik tespit edilmedi'
    })

out = ROOT / 'hafta2_150_yer_veri_denetimi.csv'
if report:
    with out.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(report[0]))
        w.writeheader()
        w.writerows(report)
print('\nVOYAGEAI - 2. HAFTA TOPLU DENETIM')
print('Veritabanindaki toplam kayit:', len(report))
for city, count in sorted(Counter(r['sehir'] for r in report).items()):
    print(f'{city}: {count} yer')
print('Gecici kayit:', sum(r['veri_durumu'] in ('aday','ozel_inceleme') for r in report))
print('Koordinati eksik:', sum('Giriş koordinatı yok' in r['eksik_kontroller'] for r in report))
print('Ucreti eksik:', sum('Ücret bilinmiyor' in r['eksik_kontroller'] for r in report))
print('Kaynak ziyaret teyidi eklenen:', sum(bool(r['resmi_ziyaret_kaynagi']) for r in report))
print('Rapor:', out)
print('Veritabaninda degisiklik YAPILMADI.')
