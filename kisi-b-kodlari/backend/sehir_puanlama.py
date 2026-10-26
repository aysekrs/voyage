
import csv
from pathlib import Path

from sqlalchemy import select, func, case

from database import SessionLocal
from city_models import Sehir, Yer


KLASOR = Path(__file__).resolve().parent
CIKTI = KLASOR / "sehir_puanlama_taslagi.csv"


def main():
    db = SessionLocal()

    try:
        sorgu = (
            select(
                Sehir.sehir_id,
                Sehir.ulke,
                Sehir.ad,
                func.count(Yer.yer_id).label("toplam_yer"),
                func.sum(
                    case((Yer.kategori == "tarih", 1), else_=0)
                ).label("tarih"),
                func.sum(
                    case((Yer.kategori == "doğa", 1), else_=0)
                ).label("doga"),
                func.sum(
                    case((Yer.kategori == "yemek", 1), else_=0)
                ).label("yemek"),
                func.sum(
                    case((Yer.kategori == "gece_hayati", 1), else_=0)
                ).label("gece")
            )
            .outerjoin(
                Yer,
                Sehir.sehir_id == Yer.sehir_id
            )
            .group_by(
                Sehir.sehir_id,
                Sehir.ulke,
                Sehir.ad
            )
            .order_by(
                Sehir.ulke,
                Sehir.ad
            )
        )

        kayitlar = db.execute(sorgu).all()

        with CIKTI.open(
            "w",
            encoding="utf-8-sig",
            newline=""
        ) as dosya:

            writer = csv.writer(dosya)

            writer.writerow([
                "sehir_id",
                "ulke",
                "sehir",
                "toplam_yer",
                "tarih_sayisi",
                "doga_sayisi",
                "yemek_sayisi",
                "gece_hayati_sayisi",
                "veri_durumu",
                "doga_puani",
                "yemek_puani",
                "tarih_puani",
                "gece_hayati_puani"
            ])

            for kayit in kayitlar:
                toplam = kayit.toplam_yer

                if toplam == 0:
                    durum = "VERI_YOK"
                elif toplam < 5:
                    durum = "AZ_VERI"
                else:
                    durum = "INCELEMEYE_UYGUN"

                writer.writerow([
                    kayit.sehir_id,
                    kayit.ulke,
                    kayit.ad,
                    toplam,
                    kayit.tarih or 0,
                    kayit.doga or 0,
                    kayit.yemek or 0,
                    kayit.gece or 0,
                    durum,
                    "",
                    "",
                    "",
                    ""
                ])

        print("Sehir puanlama taslagi olusturuldu.")
        print("Toplam sehir:", len(kayitlar))
        print("Dosya:", CIKTI.name)
        print("Veritabaninda degisiklik yapilmadi.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
