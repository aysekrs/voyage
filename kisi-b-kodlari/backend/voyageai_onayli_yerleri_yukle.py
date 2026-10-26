"""Only human-approved, checked records are imported into yerler.
Usage from backend folder:
  .\\venv\\Scripts\\python.exe voyageai_onayli_yerleri_yukle.py --csv voyageai_98_incelemeye_hazir.csv
  .\\venv\\Scripts\\python.exe voyageai_onayli_yerleri_yukle.py --csv voyageai_98_incelemeye_hazir.csv --apply
Requires existing database.py SessionLocal and sehirler/yerler schema.
"""
import argparse,csv,re,unicodedata
from pathlib import Path
from sqlalchemy import text
from database import SessionLocal

def normalized(s):
    s=unicodedata.normalize('NFKD',str(s).casefold().replace('ı','i'))
    return ''.join(c for c in s if c.isalnum())

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--csv',default='voyageai_98_incelemeye_hazir.csv')
    p.add_argument('--apply',action='store_true')
    args=p.parse_args()
    rows=list(csv.DictReader(open(args.csv,encoding='utf-8-sig',newline='')))
    with SessionLocal() as db:
        existing=db.execute(text('SELECT sehir_id,ad FROM yerler')).mappings().all()
        known={(int(r['sehir_id']),normalized(r['ad'])) for r in existing}
        additions=[]; reasons={}
        for r in rows:
            def reject(why):reasons[why]=reasons.get(why,0)+1
            if (r.get('kayit_onayi') or '').strip().lower()!='evet':reject('onay bekliyor');continue
            if (r.get('koordinat_dogrulama') or '').strip().lower()!='dogrulandi':reject('koordinat dogrulanmadi');continue
            if not r.get('ziyaret_suresi') or not r.get('ortalama_ucret'):reject('sure/ucret eksik');continue
            try:
                sid=int(r['sehir_id']);lat=float(r['enlem']);lon=float(r['boylam']);duration=int(r['ziyaret_suresi']);fee=float(r['ortalama_ucret'])
                if not (-90<=lat<=90 and -180<=lon<=180 and duration>0 and fee>=0):raise ValueError()
            except (ValueError,TypeError):reject('gecersiz sayisal veri');continue
            key=(sid,normalized(r['ad']))
            if key in known:reject('tekrar');continue
            known.add(key)
            additions.append(dict(sehir_id=sid,ad=r['ad'],kategori=r.get('onerilen_kategori') or r['kategori'],enlem=lat,boylam=lon,ziyaret_suresi=duration,ortalama_ucret=fee))
        print('Yeni onayli kayit:',len(additions),'Atlananlar:',reasons)
        if not args.apply:
            print('ONIZLEME: veritabanina dokunulmadi. Gercek ekleme icin --apply gerekir.')
            return
        if not additions:
            print('Onayli ve eksiksiz kayit yok. Hicbir sey eklenmedi.')
            return
        db.execute(text('''INSERT INTO yerler(sehir_id,ad,kategori,enlem,boylam,ziyaret_suresi,ortalama_ucret)
            VALUES (:sehir_id,:ad,:kategori,:enlem,:boylam,:ziyaret_suresi,:ortalama_ucret)'''),additions)
        db.commit()
        print('Veritabanina eklenen:',len(additions))
if __name__=='__main__':main()
