
from openpyxl import load_workbook
from pathlib import Path

dosya = Path(__file__).parent / "VoyageAI_2_Hafta_98_Yer_Duzenli.xlsx"

wb = load_workbook(dosya, read_only=True, data_only=True)

print("VOYAGEAI - 2. HAFTA KONTROLU")
print("-" * 35)

toplam = 0

sehirler = [
    "İstanbul",
    "Paris",
    "Viyana",
    "Amsterdam",
    "Berlin"
]

for sehir in sehirler:
    sayfa = wb[sehir]

    yerler = [
        satir
        for satir in sayfa.iter_rows(
            min_row=2, values_only=True
        )
        if satir[0] is not None
    ]

    print(f"{sehir}: {len(yerler)} yer")
    toplam += len(yerler)

print("-" * 35)
print(f"TOPLAM: {toplam} yer")

assert toplam == 98, "Beklenen yer sayisi 98 degil!"

print("TEST BASARILI")

wb.close()
