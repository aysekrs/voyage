import csv
from pathlib import Path
from sqlalchemy import select
from database import SessionLocal
from city_models import Yer

DOSYA = Path(__file__).resolve().parent / "ziyaret_sureleri.csv"


def main():
    with DOSYA.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    kayitlar = []
    gorulen = set()
    for row in rows:
        if row["inceleme_durumu"] != "TAHMIN":
            continue  # INCELE kayıtları daha sonra onaylanacak
        yer_id = int(row["yer_id"])
        sure = int(row["onerilen_sure"])
        if yer_id in gorulen or not 15 <= sure <= 720:
            raise ValueError(f"Tekrarli ID veya gecersiz sure: {yer_id}")
        gorulen.add(yer_id)
        kayitlar.append((yer_id, sure, row["yer_adi"]))

    print(f"CSV'de {len(kayitlar)} normal tahmin var. INCELE olanlar atlanacak.")
    db = SessionLocal()
    try:
        guncellenecek = []
        for yer_id, sure, ad in kayitlar:
            yer = db.get(Yer, yer_id)
            if yer is None:
                raise ValueError(f"Veritabaninda bulunamayan ID: {yer_id}")
            if yer.ad != ad:
                raise ValueError(f"ID {yer_id} icin ad uyusmazligi: {yer.ad} / {ad}")
            if yer.ziyaret_suresi is None:
                guncellenecek.append((yer, sure))
        print(f"Veritabaninda suresi bos olan {len(guncellenecek)} yer guncellenebilir.")
        cevap = input("Bu TAHMIN surelerini kaydetmek icin EVET yaz (aksi halde iptal): ").strip()
        if cevap != "EVET":
            print("Iptal edildi. Veritabani degismedi.")
            return
        for yer, sure in guncellenecek:
            yer.ziyaret_suresi = sure
        db.commit()
        print(f"Basarili: {len(guncellenecek)} kayit guncellendi.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
