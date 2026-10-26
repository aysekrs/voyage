
import csv
import time
from pathlib import Path

import requests

KLASOR = Path(__file__).resolve().parent

# İlk aşamada yalnızca 5 yer test ediyoruz
YERLER = [
    ("Ayasofya", "İstanbul", "Türkiye"),
    ("Topkapı Sarayı", "İstanbul", "Türkiye"),
    ("Galata Kulesi", "İstanbul", "Türkiye"),
    ("Sultanahmet Camii", "İstanbul", "Türkiye"),
    ("Gülhane Parkı", "İstanbul", "Türkiye"),
]

URL = "https://nominatim.openstreetmap.org/search"


USER_AGENT = "VoyageAI-OgrenciProjesi/1.0 (email: nazlixakpnr@gmail.com)"

sonuclar = []

for yer_adi, sehir, ulke in YERLER:

    print("Araniyor:", yer_adi)

    try:
        response = requests.get(
            URL,
            params={
                "q": f"{yer_adi}, {sehir}, {ulke}",
                "format": "json",
                "limit": 1
            },
            headers={"User-Agent": USER_AGENT},
            timeout=20
        )

        response.raise_for_status()
        data = response.json()

        if data:
            sonuc = data[0]

            sonuclar.append({
                "ulke": ulke,
                "sehir": sehir,
                "ad": yer_adi,
                "enlem": sonuc["lat"],
                "boylam": sonuc["lon"],
                "bulunan_adres": sonuc["display_name"]
            })

            print("Aday koordinat bulundu!")
        else:
            print("Sonuc bulunamadi:", yer_adi)

    except requests.RequestException as hata:
        print("Baglanti hatasi:", hata)
        break

    # Servisi yoğun kullanmamak için bekliyoruz
    time.sleep(1.5)

with open(
    KLASOR / "koordinat_adaylari.csv",
    "w",
    encoding="utf-8-sig",
    newline=""
) as file:

    kolonlar = [
        "ulke", "sehir", "ad",
        "enlem", "boylam", "bulunan_adres"
    ]

    writer = csv.DictWriter(
        file,
        fieldnames=kolonlar
    )

    writer.writeheader()
    writer.writerows(sonuclar)

print("Koordinat adaylari CSV dosyasina kaydedildi!")
