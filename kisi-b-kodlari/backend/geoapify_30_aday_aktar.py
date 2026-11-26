"""Geoapify CSV'sinden 1. siradaki konumlari aday tablosuna guvenli aktar.
Mevcut gecerli konumlari degistirmez, ana yerler tablosunu degistirmez.
Ilk once onizleme yapar; kullanici EVET derse tek transaction ile yazar.
"""
import csv
import math
from pathlib import Path
from sqlalchemy import text
from database import SessionLocal

CSV_PATH = Path(__file__).resolve().parent / 'VoyageAI_30_Koordinat_Adaylari_Kontrol.csv'
VALID_STATUSES = {'MANUEL_DOGRULAMA_GEREKLI', 'KULLANICI_KONTROL_EDILDI', 'KONTROL_EDILDI'}

def normal(s):
    return ' '.join(str(s or '').casefold().split())

def main():
    if not CSV_PATH.is_file():
        raise SystemExit('CSV bulunamadi: ' + str(CSV_PATH))
    with CSV_PATH.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f, delimiter=';')
        required = {'yer_id', 'ulke', 'sehir', 'gezilecek_yer', 'aday_sirasi', 'enlem', 'boylam', 'durum'}
        if not required.issubset(reader.fieldnames or []):
            raise SystemExit('CSV kolonlari eksik ya da ayirici yanlis. Beklenen ; ile ayrilmis dosya.')
        rows = list(reader)
    if not rows:
        raise SystemExit('CSV bos.')

    # Her yere ait birinci Geoapify sonucunu al (rastgele 2./3. adayi karistirma).
    grouped = {}
    for r in rows:
        grouped.setdefault(r['yer_id'].strip(), []).append(r)

    plan, issues = [], []
    with SessionLocal() as db:
        for key, options in grouped.items():
            try:
                yer_id = int(key)
            except ValueError:
                issues.append(f'{key}: gecersiz yer_id')
                continue
            rank1 = [r for r in options if str(r['aday_sirasi']).strip() == '1']
            if len(rank1) != 1:
                issues.append(f'{yer_id}: 1. aday yok ya da birden fazla')
                continue
            r = rank1[0]
            if r['durum'].strip() not in VALID_STATUSES:
                issues.append(f'{yer_id}: uygun arama sonucu yok ({r["durum"]})')
                continue
            try:
                lat = float(r['enlem'].replace(',', '.'))
                lon = float(r['boylam'].replace(',', '.'))
                if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
                    raise ValueError('koordinat aralik disi')
            except (ValueError, TypeError):
                issues.append(f'{yer_id}: koordinat gecersiz')
                continue
            dbrow = db.execute(text('''
                SELECT s.ulke, s.ad AS sehir, y.ad AS gezilecek_yer, y.enlem, y.boylam
                FROM yerler y JOIN sehirler s ON s.sehir_id = y.sehir_id
                WHERE y.yer_id = :id
            '''), {'id': yer_id}).mappings().first()
            if not dbrow:
                issues.append(f'{yer_id}: veritabaninda yok')
                continue
            if any(normal(r[c]) != normal(dbrow[c]) for c in ('ulke','sehir','gezilecek_yer')):
                issues.append(f'{yer_id}: sehir/ulke/yer adi CSV ile veritabaninda uyusmuyor')
                continue
            main_valid = (dbrow['enlem'] is not None and dbrow['boylam'] is not None
                          and -90 <= dbrow['enlem'] <= 90 and -180 <= dbrow['boylam'] <= 180)
            if main_valid:
                issues.append(f'{yer_id}: ana tabloda zaten gecerli koordinat var; atlandi')
                continue
            current = db.execute(text('SELECT enlem, boylam, durum FROM koordinat_adaylari WHERE yer_id=:id'), {'id':yer_id}).mappings().first()
            if current and current['enlem'] is not None and current['boylam'] is not None and -90 <= current['enlem'] <= 90 and -180 <= current['boylam'] <= 180:
                issues.append(f'{yer_id}: mevcut gecerli aday var; atlandi')
                continue
            plan.append((yer_id, lat, lon, 'UPDATE' if current else 'INSERT', r['gezilecek_yer']))
        print(f'CSV: {len(rows)} satir, {len(grouped)} farkli yer')
        print(f'Aktarilacak aday: {len(plan)} | Atlanan/hata: {len(issues)}')
        for msg in issues:
            print('  ATLANDI:', msg)
        for yer_id, lat, lon, action, name in plan:
            print(f'  {action:6} yer_id={yer_id:3} {name}: {lat:.6f}, {lon:.6f}')
        if not plan:
            print('Aktarilacak yeni aday yok. Degisiklik yapilmadi.')
            return
        print('\nDIKKAT: CSV icindeki HER YER ICIN ILK GEOAPIFY SONUCU aktarilacak.')
        print('Bunlar onaylanmis ziyaretci giris koordinatlari olarak isaretlenmeyecek.')
        if input('Ilk adaylari kontrol ettiysen yazmak icin EVET yaz: ').strip() != 'EVET':
            print('Iptal edildi; hicbir sey degismedi.')
            return
        try:
            for yer_id, lat, lon, action, _ in plan:
                args = {'id':yer_id, 'lat':lat, 'lon':lon, 'durum':'KULLANICI_KONTROL_EDILDI', 'kaynak':'Geoapify CSV - ilk aday; yer/sehir kontrolu'}
                if action == 'UPDATE':
                    db.execute(text('''UPDATE koordinat_adaylari
                                       SET enlem=:lat, boylam=:lon, durum=:durum,
                                           kaynak=:kaynak, guncelleme_zamani=NOW()
                                       WHERE yer_id=:id'''), args)
                else:
                    db.execute(text('''INSERT INTO koordinat_adaylari
                                       (yer_id,enlem,boylam,durum,kaynak)
                                       VALUES (:id,:lat,:lon,:durum,:kaynak)'''), args)
            db.commit()
            print(f'BASARILI: {len(plan)} aday koordinat kaydedildi. Ana yerler tablosu degismedi.')
        except Exception:
            db.rollback()
            print('HATA: Islem geri alindi (ROLLBACK).')
            raise

if __name__ == '__main__':
    main()
