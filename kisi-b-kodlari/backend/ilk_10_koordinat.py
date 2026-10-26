
import csv
from pathlib import Path

KLASOR = Path(__file__).resolve().parent

GIRIS = KLASOR / "koordinat_on_kontrol.csv"
CIKIS = KLASOR / "ilk_10_koordinat_kontrol.csv"

with GIRIS.open(
    "r", encoding="utf-8-sig", newline=""
) as dosya:
    reader = csv.DictReader(dosya)

    alanlar = reader.fieldnames

    uygunlar = [
        satir for satir in reader
        if satir["durum"] == "IKI_TUR_UYUMLU_KONTROL"
        and satir["aday_enlem"]
        and satir["aday_boylam"]
    ]

ilk_10 = uygunlar[:10]

with CIKIS.open(
    "w", encoding="utf-8-sig", newline=""
) as dosya:
    writer = csv.DictWriter(
        dosya, fieldnames=alanlar
    )
    writer.writeheader()
    writer.writerows(ilk_10)

print("Toplam uyumlu aday:", len(uygunlar))
print("Kontrole ayrilan:", len(ilk_10))
print("Olusturulan dosya:", CIKIS.name)

for yer in ilk_10:
    print(
        yer["yer_id"],
        "-",
        yer["sehir"],
        "-",
        yer["yer_adi"]
    )
