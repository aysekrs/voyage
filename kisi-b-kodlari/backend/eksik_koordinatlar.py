
import csv
from pathlib import Path

from sqlalchemy import select, or_

from database import SessionLocal
from city_models import Sehir, Yer

KLASOR = Path(__file__).resolve().parent

DOSYA = KLASOR / "eksik_koordinatlar.csv"


def eksikleri_listele():

    db = SessionLocal()

    try:
        sorgu = (
            select(
                Sehir.ulke,
                Sehir.ad.label("sehir"),
                Yer.ad.label("yer")
            )
            .join(Yer, Yer.sehir_id == Sehir.sehir_id)
            .where(
                or_(
                    Yer.enlem.is_(None),
                    Yer.boylam.is_(None)
                )
            )
            .order_by(
                Sehir.ulke,
                Sehir.ad,
                Yer.ad
            )
        )

        sonuc = db.execute(sorgu).all()

        with DOSYA.open(
            "w",
            encoding="utf-8-sig",
            newline=""
        ) as file:

            writer = csv.writer(file)

            writer.writerow([
                "ulke",
                "sehir",
                "ad"
            ])

            for satir in sonuc:
                writer.writerow([
                    satir.ulke,
                    satir.sehir,
                    satir.yer
                ])

        print("Eksik koordinatlar listelendi!")
        print("Eksik yer sayisi:", len(sonuc))
        print("Dosya:", DOSYA.name)

    finally:
        db.close()


if __name__ == "__main__":
    eksikleri_listele()
