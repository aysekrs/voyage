"""SADECE TEST İÇİN: yerler tablosundaki boş koordinat, ziyaret süresi
ve ücretleri B'nin repodaki çalışma dosyalarından doldurur.

- Sadece BOŞ alanları doldurur, dolu bir değeri asla değiştirmez.
- Koordinatlar B'nin henüz onaylamadığı adaylardır ("BELIRGIN_YANLIS"
  ve "KOORDINAT_YOK" olanlar alınmaz). Bazıları yanlış olabilir.
- Ücretler gerçek değil, kategoriye göre kaba tahmindir.
- B kendi doğrulanmış verisini gönderince bu script'e gerek kalmaz.

Çalıştırmak için backend klasöründe:  py test_verisi_doldur.py
"""
import csv
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv()

B_KLASORU = Path(__file__).resolve().parent.parent / "kisi-b-kodlari" / "backend"

# Kaba tahmini giriş ücretleri (TL, kişi başı) - SADECE TEST
TAHMINI_UCRET = {"tarih": 300, "doğa": 0, "yemek": 450, "gece_hayati": 600}

ALINMAYAN_KOORDINAT = {"BELIRGIN_YANLIS", "KOORDINAT_YOK"}


def oku(dosya):
    with open(B_KLASORU / dosya, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def anahtar(sehir, ad):
    return (sehir.strip().lower(), ad.strip().lower())


def koordinatlar():
    sonuc = {}
    for r in oku("voyageai_koordinat_inceleme.csv"):
        if r["kontrol_durumu"] in ALINMAYAN_KOORDINAT or not r["enlem"] or not r["boylam"]:
            continue
        enlem, boylam = float(r["enlem"]), float(r["boylam"])
        if -90 <= enlem <= 90 and -180 <= boylam <= 180:
            sonuc[anahtar(r["sehir"], r["ad"])] = (enlem, boylam)
    return sonuc


def sureler():
    sonuc = {}
    for r in oku("ziyaret_sureleri.csv"):
        if r["onerilen_sure"]:
            sonuc[anahtar(r["sehir"], r["yer_adi"])] = int(float(r["onerilen_sure"]))
    # İncelenmiş süreler varsa onları tercih et
    for r in oku("voyageai_34_ziyaret_suresi_tahminleri.csv"):
        if r["onaylanan_sure"]:
            sonuc[anahtar(r["sehir"], r["yer_adi"])] = int(float(r["onaylanan_sure"]))
    return sonuc


def main():
    koord, sure = koordinatlar(), sureler()
    sayac = {"koordinat": 0, "sure": 0, "ucret": 0}

    with psycopg.connect(os.environ["DATABASE_URL"]) as db:
        yerler = db.execute(
            """
            SELECT y.yer_id, s.ad AS sehir, y.ad, y.kategori,
                   y.enlem, y.boylam, y.ziyaret_suresi, y.ortalama_ucret
            FROM yerler y JOIN sehirler s ON s.sehir_id = y.sehir_id
            """
        ).fetchall()

        for yer_id, sehir, ad, kategori, enlem, boylam, ziyaret, ucret in yerler:
            k = anahtar(sehir, ad)

            if (enlem is None or boylam is None) and k in koord:
                db.execute(
                    "UPDATE yerler SET enlem = %s, boylam = %s WHERE yer_id = %s",
                    (*koord[k], yer_id),
                )
                sayac["koordinat"] += 1

            if not ziyaret and k in sure:
                db.execute(
                    "UPDATE yerler SET ziyaret_suresi = %s WHERE yer_id = %s",
                    (sure[k], yer_id),
                )
                sayac["sure"] += 1

            if ucret is None and kategori in TAHMINI_UCRET:
                db.execute(
                    "UPDATE yerler SET ortalama_ucret = %s WHERE yer_id = %s",
                    (TAHMINI_UCRET[kategori], yer_id),
                )
                sayac["ucret"] += 1

    print("Doldurulan koordinat :", sayac["koordinat"])
    print("Doldurulan süre      :", sayac["sure"])
    print("Doldurulan ücret     :", sayac["ucret"])
    print("Bitti. Kontrol için: py veri_kontrol.py")


if __name__ == "__main__":
    main()
