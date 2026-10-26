"""VoyageAI: CSV verilerini var olan sehirler/yerler tablolarina aktarir.
Kullanım: backend klasorune 2 CSV ve bu dosyayi kopyalayip python voyageai_seed.py
"""
import csv
from pathlib import Path
from sqlalchemy import select
from database import SessionLocal
from city_models import Sehir, Yer

KLASOR = Path(__file__).resolve().parent


def oku(ad):
    with (KLASOR / ad).open('r', encoding='utf-8-sig', newline='') as f:
        yield from csv.DictReader(f)


def deger(s):
    return (s or '').strip() or None


def bul_sehir(db, ulke, ad):
    eslesenler = db.execute(select(Sehir).where(Sehir.ulke == ulke, Sehir.ad == ad)).scalars().all()
    if len(eslesenler) > 1:
        raise ValueError(f'Ayni ulke ve sehirden birden fazla kayit var: {ulke} / {ad}')
    return eslesenler[0] if eslesenler else None


def yukle():
    db = SessionLocal()
    eklenen_sehir = eklenen_yer = atlanan_sehir = atlanan_yer = 0
    try:
        for row in oku('voyageai_sehirler.csv'):
            ulke, ad = row['ulke'].strip(), row['ad'].strip()
            sehir = bul_sehir(db, ulke, ad)
            if sehir is not None:
                atlanan_sehir += 1
                continue
            db.add(Sehir(
                ad=ad,
                ulke=ulke,
                havalimani_kodu=deger(row['havalimani_kodu']),
                para_birimi=deger(row['para_birimi']),
                doga_puani=None,
                yemek_puani=None,
                tarih_puani=None,
                gece_hayati_puani=None,
                gunluk_yemek_maliyeti=None,
            ))
            db.flush()
            eklenen_sehir += 1

        for row in oku('voyageai_yerler.csv'):
            ulke, ad, yer_adi = row['ulke'].strip(), row['sehir'].strip(), row['ad'].strip()
            sehir = bul_sehir(db, ulke, ad)
            if sehir is None:
                raise ValueError(f'Sehir CSV dosyasinda bulunamadi: {ulke} / {ad}')
            mevcut = db.execute(
                select(Yer).where(Yer.sehir_id == sehir.sehir_id, Yer.ad == yer_adi)
            ).scalars().first()
            if mevcut is not None:
                atlanan_yer += 1
                continue
            db.add(Yer(
                sehir_id=sehir.sehir_id,
                ad=yer_adi,
                kategori=deger(row['kategori']),
                enlem=None,
                boylam=None,
                ziyaret_suresi=None,
                ortalama_ucret=None,
            ))
            eklenen_yer += 1

        db.commit()
        print(f'Tamamlandi! Yeni sehir: {eklenen_sehir}, mevcut sehir: {atlanan_sehir}')
        print(f'Yeni yer: {eklenen_yer}, mevcut yer: {atlanan_yer}')
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == '__main__':
    yukle()
