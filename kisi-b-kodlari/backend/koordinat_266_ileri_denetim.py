"""VoyageAI koordinat adaylarını çevrimdışı ve veritabanına dokunmadan denetler.
Çalıştırma: python koordinat_266_ileri_denetim.py
"""
import csv
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'voyageai_266_koordinat_kontrol_listesi.csv'
OUTPUT = ROOT / 'koordinat_266_ileri_denetim.csv'


def number(value):
    try:
        n = float(str(value or '').strip())
        return n if math.isfinite(n) else None
    except ValueError:
        return None


def norm(text):
    return ' '.join(str(text or '').casefold().strip().split())


def main():
    if not SOURCE.exists():
        raise SystemExit(f'Girdi dosyasi yok: {SOURCE.name}')
    with SOURCE.open(encoding='utf-8-sig', newline='') as handle:
        rd = csv.DictReader(handle)
        needed = {'yer_id','ulke','sehir','yer_adi','durum','aday_enlem','aday_boylam',
                  'ilk_tur_adres','ikinci_tur_adres'}
        missing = needed - set(rd.fieldnames or [])
        if missing:
            raise SystemExit(f'Eksik CSV sutunlari: {sorted(missing)}')
        rows = list(rd)

    id_counts = Counter(r['yer_id'].strip() for r in rows)
    coordinates = defaultdict(list)
    for row in rows:
        lat, lon = number(row['aday_enlem']), number(row['aday_boylam'])
        if lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180:
            coordinates[(round(lat, 5), round(lon, 5))].append(row['yer_id'])

    results=[]
    for row in rows:
        reasons=[]
        lat, lon = number(row['aday_enlem']), number(row['aday_boylam'])
        valid = lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180
        if id_counts[row['yer_id'].strip()] != 1:
            reasons.append('TEKRARLI_YER_ID')
        if not valid:
            reasons.append('GECERLI_KOORDINAT_YOK')
        else:
            same = coordinates[(round(lat, 5), round(lon, 5))]
            if len(set(same)) > 1:
                reasons.append('FARKLI_YERLERDE_AYNI_KOORDINAT')

        address1 = norm(row['ilk_tur_adres'])
        address2 = norm(row['ikinci_tur_adres'])
        addresses = [x for x in [address1,address2] if x]
        town = norm(row['sehir'])
        # Basit ad metni kontrolü: Türkçe/yerel-İngilizce karşılıklar kaçabilir.
        if addresses and town not in ' '.join(addresses):
            reasons.append('ADRESTE_SEHIR_ADI_GORUNMUYOR')
        if not addresses:
            reasons.append('ADRES_BILGISI_YOK')
        if addresses and all(len(x.split(',')) <= 2 for x in addresses):
            reasons.append('GENEL_ADRES_OLABILIR')

        base = row['durum'].strip()
        if base == 'YENI_ARAMA_GEREKLI' or not valid:
            group = 'YENI_ARAMA_GEREKLI'
        elif base != 'ONCELIKLI_ADAY' or reasons:
            group = 'EK_INCELEME'
        else:
            group = 'ONCELIKLI_ADAY_KONTROL'
        row_out = dict(row)
        row_out['ileri_denetim'] = group
        row_out['risk_isaretleri'] = ' | '.join(reasons)
        row_out['otomatik_dogrulandi'] = 'HAYIR'
        results.append(row_out)

    fields = list(rd.fieldnames or []) + ['ileri_denetim','risk_isaretleri','otomatik_dogrulandi']
    with OUTPUT.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)

    print('Toplam incelenen:',len(results))
    for group, count in Counter(x['ileri_denetim'] for x in results).most_common():
        print(group + ':', count)
    print('Rapor:',OUTPUT.name)
    print('Veritabani DEGISTIRILMEDI. Hicbir koordinat otomatik onaylanmadi.')

if __name__ == '__main__':
    main()
