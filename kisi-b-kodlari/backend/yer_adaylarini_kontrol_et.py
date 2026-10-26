
import csv
import unicodedata
from collections import defaultdict
from pathlib import Path

from sqlalchemy import text
from database import SessionLocal

KLASOR = Path(__file__).resolve().parent
GIRIS = KLASOR / "yeni_yer_adaylari.csv"
CIKIS = KLASOR / "yer_inceleme_listesi.csv"

def normalize(ad):
    ad = ad.casefold().replace("ı", "i")
    ad = unicodedata.normalize("NFKD", ad)
    return "".join(
        h for h in ad
        if h.isalnum()
    )

def main():
    with GIRIS.open(
        encoding="utf-8-sig", newline=""
    ) as f:
        adaylar = list(csv.DictReader(f))

    db = SessionLocal()

    try:
        mevcut = db.execute(text("""
            SELECT sehir_id, ad
            FROM yerler
        """)).mappings().all()

        sayilar = db.execute(text("""
            SELECT sehir_id, COUNT(*) AS sayi
            FROM yerler
            GROUP BY sehir_id
        """)).mappings().all()
    finally:
        db.close()

    bilinen = defaultdict(set)
    mevcut_sayilar = defaultdict(int)

    for yer in mevcut:
        bilinen[yer["sehir_id"]].add(
            normalize(yer["ad"])
        )

    for satir in sayilar:
        mevcut_sayilar[satir["sehir_id"]] = satir["sayi"]

    hedefler = {
        sehir_id: max(
            0, 30 - mevcut_sayilar[sehir_id]
        )
        for sehir_id in (8, 82, 39, 1, 24)
    }

    secilen_sayisi = defaultdict(int)
    gorulen_adaylar = defaultdict(set)

    for aday in adaylar:
        sehir_id = int(aday["sehir_id"])
        ad = normalize(aday["ad"])

        if (
            ad in bilinen[sehir_id]
            or ad in gorulen_adaylar[sehir_id]
        ):
            aday["durum"] = "olasi_tekrar"
        elif secilen_sayisi[sehir_id] < hedefler[sehir_id]:
            aday["durum"] = "incele_ve_onayla"
            secilen_sayisi[sehir_id] += 1
        else:
            aday["durum"] = "yedek_aday"

        gorulen_adaylar[sehir_id].add(ad)

    alanlar = list(adaylar[0].keys())

    with CIKIS.open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        yazici = csv.DictWriter(
            f, fieldnames=alanlar
        )
        yazici.writeheader()
        yazici.writerows(adaylar)

    print("\nVOYAGEAI - VERI KONTROLU")
    print("-----------------------")

    for sehir_id, isim in [
        (8, "Paris"),
        (82, "Viyana"),
        (39, "Amsterdam"),
        (1, "Istanbul"),
        (24, "Berlin")
    ]:
        print(
            f"{isim}: {secilen_sayisi[sehir_id]}"
            f"/{hedefler[sehir_id]} inceleme adayi"
        )

    print("\nDurumlar:")
    durum_sayilari = defaultdict(int)

    for aday in adaylar:
        durum_sayilari[aday["durum"]] += 1

    for durum, sayi in durum_sayilari.items():
        print(f"{durum}: {sayi}")

    print(f"\nKontrol dosyasi: {CIKIS}")
    print("Veritabanina henuz yeni yer eklenmedi.")

if __name__ == "__main__":
    main()
