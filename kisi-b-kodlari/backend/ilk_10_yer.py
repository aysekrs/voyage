
import csv
from pathlib import Path

KLASOR = Path(__file__).resolve().parent

giris = KLASOR / "eksik_koordinatlar.csv"
cikis = KLASOR / "ilk_10_yer.csv"

with giris.open(
    "r",
    encoding="utf-8-sig",
    newline=""
) as file:
    reader = csv.DictReader(file)
    ilk_on = []

    for satir in reader:
        ilk_on.append(satir)

        if len(ilk_on) == 10:
            break

with cikis.open(
    "w",
    encoding="utf-8-sig",
    newline=""
) as file:
    writer = csv.DictWriter(
        file,
        fieldnames=["ulke", "sehir", "ad"]
    )

    writer.writeheader()
    writer.writerows(ilk_on)

print("Ilk 10 eksik yer hazirlandi!")

for yer in ilk_on:
    print(
        yer["ulke"],
        "-",
        yer["sehir"],
        "-",
        yer["ad"]
    )
