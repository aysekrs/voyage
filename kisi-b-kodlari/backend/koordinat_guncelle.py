
import csv
from pathlib import Path

from sqlalchemy import select

from database import SessionLocal
from city_models import Sehir, Yer

KLASOR = Path(__file__).resolve().parent
DOSYA = KLASOR / "koordinat_onayli.csv"


def koordinatlari_guncelle():
    db = SessionLocal()
    guncellenen = 0

    try:
        with DOSYA.open(
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as file:

            reader = csv.DictReader(file)

            for row in reader:
                ulke = row["ulke"].strip()
                sehir_adi = row["sehir"].strip()
                yer_adi = row["ad"].strip()

                enlem = float(row["enlem"])
                boylam = float(row["boylam"])

                if not (-90 <= enlem <= 90):
                    raise ValueError("Gecersiz enlem")

                if not (-180 <= boylam <= 180):
                    raise ValueError("Gecersiz boylam")

                # Önce ülke ve şehir eşleşmesini bul
                sehir = db.execute(
                    select(Sehir).where(
                        Sehir.ad == sehir_adi,
                        Sehir.ulke == ulke
                    )
                ).scalar_one_or_none()

                if sehir is None:
                    print("Sehir bulunamadi:", sehir_adi)
                    continue

                # İlgili gezilecek yeri bul
                yer = db.execute(
                    select(Yer).where(
                        Yer.sehir_id == sehir.sehir_id,
                        Yer.ad == yer_adi
                    )
                ).scalar_one_or_none()

                if yer is None:
                    print("Yer bulunamadi:", yer_adi)
                    continue

                # Onaylanan koordinatları kaydet
                yer.enlem = enlem
                yer.boylam = boylam

                guncellenen += 1
                print("Guncellendi:", yer_adi)

        db.commit()

        print(
            "Toplam guncellenen yer:",
            guncellenen
        )

    except Exception as hata:
        db.rollback()
        print("Hata:", hata)
        raise

    finally:
        db.close()


if __name__ == "__main__":
    koordinatlari_guncelle()
