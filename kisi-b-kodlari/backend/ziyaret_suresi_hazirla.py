
import csv
from pathlib import Path

from sqlalchemy import select

from database import SessionLocal
from city_models import Sehir, Yer


# Kategorilere göre başlangıç süresi (dakika)
SURELER = {
    "tarih": 90,
    "doğa": 120,
    "yemek": 60,
    "gece_hayati": 120
}

# Bu kelimeleri içeren yerler ayrıca incelenecek.
OZEL_KELIMELER = [
    "antik kent",
    "antik tiyatro",
    "müze",
    "museum",
    "national park",
    "milli park",
    "vadi",
    "kanyon",
    "göl",
    "goreme",
    "göreme",
    "piramit"
]

KLASOR = Path(__file__).resolve().parent
DOSYA = KLASOR / "ziyaret_sureleri.csv"


def ziyaret_surelerini_hazirla():
    db = SessionLocal()

    try:
        sorgu = (
            select(
                Yer.yer_id,
                Yer.ad.label("yer_adi"),
                Yer.kategori,
                Yer.ziyaret_suresi,
                Sehir.ad.label("sehir"),
                Sehir.ulke
            )
            .join(Sehir, Yer.sehir_id == Sehir.sehir_id)
            .order_by(Sehir.ulke, Sehir.ad, Yer.ad)
        )

        kayitlar = db.execute(sorgu).all()

        with DOSYA.open(
            "w",
            encoding="utf-8-sig",
            newline=""
        ) as dosya:

            writer = csv.writer(dosya)

            writer.writerow([
                "yer_id",
                "ulke",
                "sehir",
                "yer_adi",
                "kategori",
                "onerilen_sure",
                "inceleme_durumu"
            ])

            for kayit in kayitlar:

                kategori = (
                    kayit.kategori or ""
                ).strip().lower()

                sure = SURELER.get(kategori)

                ad = kayit.yer_adi.lower()

                if kayit.ziyaret_suresi is not None:
                    sure = kayit.ziyaret_suresi
                    durum = "MEVCUT_SURE"

                elif sure is None:
                    durum = "KATEGORI_BELIRSIZ"

                elif any(
                    kelime in ad
                    for kelime in OZEL_KELIMELER
                ):
                    durum = "INCELE"

                else:
                    durum = "TAHMIN"

                writer.writerow([
                    kayit.yer_id,
                    kayit.ulke,
                    kayit.sehir,
                    kayit.yer_adi,
                    kayit.kategori,
                    sure if sure is not None else "",
                    durum
                ])

        print("Ziyaret sureleri CSV dosyasi hazirlandi!")
        print("Toplam yer sayisi:", len(kayitlar))
        print("Dosya:", DOSYA.name)

    finally:
        db.close()


if __name__ == "__main__":
    ziyaret_surelerini_hazirla()
