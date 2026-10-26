"""VoyageAI ikinci tur koordinat aday araması.
İlk tur CSV'sini ve veritabanını DEĞİŞTİRMEZ.
Kullanım:
  python koordinat_ikinci_tur.py --limit 10
  python koordinat_ikinci_tur.py
"""
import argparse
import csv
import os
import time
from pathlib import Path
import requests
from dotenv import load_dotenv
from koordinat_toplu import request_geo, COUNTRIES

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'voyageai_koordinat_inceleme.csv'
OUTPUT = ROOT / 'koordinat_ikinci_tur_sonuclari.csv'

# İlk turda problemli olan bazı Türkçe yer adlarının yaygın uluslararası karşılıkları.
# Gerekirse listeye ekleme yapılabilir.
ALIASES = {
    'Heidelberg Kalesi': 'Heidelberg Castle',
    'Altın Çatı': 'Goldenes Dachl',
    'Efes Antik Kenti': 'Ephesus Archaeological Site',
    'Pena Sarayı': 'Palacio da Pena',
    'Sümela Manastırı': 'Sumela Monastery',
    'Frauenkirche': 'Frauenkirche Dresden',
    'Zwinger Sarayı': 'Zwinger Dresden',
    'Elbphilharmonie': 'Elbphilharmonie Hamburg',
    'Köln Katedrali': 'Cologne Cathedral',
    'Hohenzollern Köprüsü': 'Hohenzollern Bridge Cologne',
    'Englischer Garten': 'English Garden Munich',
    'Nymphenburg Sarayı': 'Nymphenburg Palace',
    'Sanssouci Sarayı': 'Sanssouci Palace Potsdam',
    'Hallstatt Gölü': 'Hallstatter See',
    'Bergisel Kayakla Atlama Tepesi': 'Bergisel Ski Jump',
    'Hellbrunn Sarayı': 'Hellbrunn Palace Salzburg',
    'Hohensalzburg Kalesi': 'Fortress Hohensalzburg',
    'Mirabell Sarayı ve Bahçeleri': 'Mirabell Palace and Gardens',
    "Mozart'ın Doğduğu Ev": 'Mozarts Geburtshaus Salzburg',
    'Aziz Stefan Katedrali': 'St Stephens Cathedral Vienna',
    'Belvedere Sarayı': 'Belvedere Palace Vienna',
    'Hofburg Sarayı': 'Hofburg Palace Vienna',
}

FIELDS = [
    'ulke','sehir','ad','eski_enlem','eski_boylam','eski_adres','eski_durum',
    'arama_adi','yeni_enlem','yeni_boylam','yeni_adres','yeni_durum','yeni_puan','not'
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()
    load_dotenv(ROOT / '.env')
    key = os.getenv('GEOAPIFY_API_KEY', '').strip()
    if not key:
        raise SystemExit('GEOAPIFY_API_KEY .env dosyasında bulunamadı.')
    if not SOURCE.exists():
        raise SystemExit('voyageai_koordinat_inceleme.csv dosyası backend klasöründe yok.')
    with SOURCE.open(encoding='utf-8-sig', newline='') as f:
        rows = [r for r in csv.DictReader(f) if r['kontrol_durumu'] != 'ADAY_ONAY_BEKLIYOR']
    if args.limit > 0:
        rows = rows[:args.limit]
    results=[]
    with requests.Session() as session:
        for i,r in enumerate(rows,1):
            alternate=ALIASES.get(r['ad'], r['ad'])
            # Arama ismini request_geo'ya geçirirken orijinal yer adını değiştirmiyoruz;
            # request_geo'nun kendi benzerlik kontrolü nedeniyle çıktı sadece ADAYDIR.
            q=dict(r)
            q['ad']=alternate
            out={
                'ulke':r['ulke'],'sehir':r['sehir'],'ad':r['ad'],
                'eski_enlem':r['enlem'],'eski_boylam':r['boylam'],
                'eski_adres':r['bulunan_adres'],'eski_durum':r['kontrol_durumu'],
                'arama_adi':alternate,'yeni_enlem':'','yeni_boylam':'',
                'yeni_adres':'','yeni_durum':'BULUNAMADI','yeni_puan':'',
                'not':'Sadece koordinat adayıdır; doğrulanmadı.'
            }
            try:
                hit=request_geo(session,q,key)
                if hit and hit['lat'] is not None and hit['lon'] is not None:
                    out.update(yeni_enlem=hit['lat'],yeni_boylam=hit['lon'],
                               yeni_adres=hit['address'],yeni_durum=hit['status'],
                               yeni_puan=hit['score'])
            except (requests.RequestException,RuntimeError) as exc:
                out['yeni_durum']='HATA'
                out['not']=str(exc)[:180]
                if isinstance(exc,RuntimeError):
                    results.append(out)
                    print(f'{i}/{len(rows)} {r["ad"]}: HATA (durduruldu)')
                    break
            results.append(out)
            print(f'{i}/{len(rows)} {r["ad"]}: {out["yeni_durum"]}')
            time.sleep(0.6)
    with OUTPUT.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(results)
    print(f'Bitti. {len(results)} kayıt -> {OUTPUT.name}')
    print('ÖNEMLİ: PostgreSQL değişmedi. Çıktıyı gözden geçirmeden yükleme.')

if __name__ == '__main__':
    main()
