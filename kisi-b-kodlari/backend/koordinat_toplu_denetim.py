"""VoyageAI: 2 Geoapify turunu kalan yerlerle topluca karşılaştırır.
Yalnızca CSV raporu üretir; PostgreSQL'i asla değiştirmez.
"""
import csv
import math
import unicodedata
from collections import Counter
from pathlib import Path
from sqlalchemy import select
from database import SessionLocal
from city_models import Sehir, Yer

ROOT = Path(__file__).resolve().parent
FIRST = ROOT / 'koordinat_sonuclari.csv'
SECOND = ROOT / 'koordinat_ikinci_tur_sonuclari.csv'
OUTPUT = ROOT / 'koordinat_toplu_denetim.csv'


def normalize(s):
    s = str(s or '').casefold().replace('ı', 'i')
    s = ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))
    return ' '.join(s.split())


def key(row):
    return (normalize(row.get('ulke')), normalize(row.get('sehir')), normalize(row.get('ad')))


def read_csv(path):
    if not path.is_file():
        raise FileNotFoundError(f'Dosya bulunamadi: {path.name}')
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def coordinates(lat, lon):
    try:
        a, b = float(lat), float(lon)
        if math.isfinite(a) and math.isfinite(b) and -90 <= a <= 90 and -180 <= b <= 180:
            return (a, b)
    except (ValueError, TypeError):
        pass
    return None


def distance_m(p, q):
    r = 6371000
    x1, x2 = math.radians(p[0]), math.radians(q[0])
    dx = x2 - x1
    dy = math.radians(q[1] - p[1])
    h = math.sin(dx/2)**2 + math.cos(x1)*math.cos(x2)*math.sin(dy/2)**2
    return 2*r*math.asin(min(1, math.sqrt(h)))


def unique_index(rows):
    idx = {}
    for r in rows:
        idx.setdefault(key(r), []).append(r)
    return idx


def first_value(row):
    if not row:
        return None
    return coordinates(row.get('enlem'), row.get('boylam'))


def second_value(row):
    if not row:
        return None
    return coordinates(row.get('yeni_enlem'), row.get('yeni_boylam'))


def main():
    first = unique_index(read_csv(FIRST))
    second = unique_index(read_csv(SECOND))
    db = SessionLocal()
    try:
        rows = db.execute(
            select(Yer.yer_id, Yer.ad, Yer.enlem, Yer.boylam, Sehir.ad.label('sehir'), Sehir.ulke)
            .join(Sehir, Yer.sehir_id == Sehir.sehir_id)
            .order_by(Sehir.ulke, Sehir.ad, Yer.ad)
        ).all()

        output = []
        for item in rows:
            if item.enlem is not None and item.boylam is not None:
                continue
            lookup = (normalize(item.ulke), normalize(item.sehir), normalize(item.ad))
            a_matches = first.get(lookup, [])
            b_matches = second.get(lookup, [])
            a = a_matches[0] if len(a_matches) == 1 else None
            b = b_matches[0] if len(b_matches) == 1 else None
            p = first_value(a)
            q = second_value(b)
            addr1 = (a or {}).get('bulunan_adres', '')
            addr2 = (b or {}).get('yeni_adres', '')
            addr = addr2 or addr1
            city_found = normalize(item.sehir) in normalize(addr) if addr and item.sehir else False
            dist = round(distance_m(p, q), 1) if p and q else None
            chosen = q or p
            reasons = []

            if len(a_matches) > 1 or len(b_matches) > 1:
                level = 'CAKISAN_KAYIT'
                reasons.append('Ayni yer icin tekrarlanan CSV satiri')
                chosen = None
            elif not p and not q:
                level = 'YENI_ARAMA_GEREKLI'
                reasons.append('Gecerli koordinat adayi yok')
            elif not city_found:
                level = 'MANUEL_INCELE'
                reasons.append('Adres metninde sehir adi bulunamadi / adres eksik')
            elif dist is not None and dist > 150:
                level = 'MANUEL_INCELE'
                reasons.append('Iki tur konumlari 150 metreden uzak')
            elif p and q and dist is not None and dist <= 150:
                level = 'ONCELIKLI_ADAY'
                reasons.append('Iki tur yaklasik ayni yerde ve adres sehirle uyumlu')
            elif (a or {}).get('eslesme_durumu') == 'GUCLU_ADAY':
                level = 'ONCELIKLI_ADAY'
                reasons.append('Ilk tur guclu aday, adres sehirle uyumlu')
            elif (b or {}).get('yeni_durum') == 'GUCLU_ADAY':
                level = 'ONCELIKLI_ADAY'
                reasons.append('Ikinci tur guclu aday, adres sehirle uyumlu')
            else:
                level = 'MANUEL_INCELE'
                reasons.append('Tek veya dusuk guvenli aday')

            if (item.enlem is None) != (item.boylam is None):
                level = 'MANUEL_INCELE'
                reasons.append('Veritabaninda koordinat cifti eksik')

            output.append({
                'yer_id': item.yer_id, 'ulke': item.ulke, 'sehir': item.sehir,
                'yer_adi': item.ad, 'durum': level,
                'aday_enlem': chosen[0] if chosen else '',
                'aday_boylam': chosen[1] if chosen else '',
                'ilk_tur_adres': addr1, 'ikinci_tur_adres': addr2,
                'ilk_tur_durum': (a or {}).get('eslesme_durumu', ''),
                'ikinci_tur_durum': (b or {}).get('yeni_durum', ''),
                'turlar_arasi_metre': dist if dist is not None else '',
                'kontrol_notu': '; '.join(reasons),
                'harita_onayi': 'BEKLIYOR',
                'onayli_enlem': '', 'onayli_boylam': ''
            })

        fields = ['yer_id','ulke','sehir','yer_adi','durum','aday_enlem','aday_boylam',
                  'ilk_tur_adres','ikinci_tur_adres','ilk_tur_durum','ikinci_tur_durum',
                  'turlar_arasi_metre','kontrol_notu','harita_onayi','onayli_enlem','onayli_boylam']
        with OUTPUT.open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(output)

        stats = Counter(r['durum'] for r in output)
        print('Toplam veritabani kaydi:',len(rows))
        print('Koordinati eksik kayit:',len(output))
        print('Ilk tur aday satiri:',sum(map(len,first.values())))
        print('Ikinci tur aday satiri:',sum(map(len,second.values())))
        for status, count in stats.most_common():
            print(f'{status}: {count}')
        print('Rapor:', OUTPUT.name)
        print('ONEMLI: Bu bir otomatik ON ELEMEDIR; konumlar kesin dogrulanmadi.')
        print('VERITABANI DEGISTIRILMEDI.')
    finally:
        db.close()

if __name__ == '__main__':
    main()
