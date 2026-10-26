
import csv
import json
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

# Şehir ID, merkez enlemi, merkez boylamı, gereken yer sayısı
SEHIRLER = {
    "Paris": (8, 48.8566, 2.3522, 18),
    "Viyana": (82, 48.2082, 16.3738, 19),
    "Amsterdam": (39, 52.3676, 4.9041, 20),
    "İstanbul": (1, 41.0082, 28.9784, 20),
    "Berlin": (24, 52.5200, 13.4050, 21),
}

API = "https://overpass-api.de/api/interpreter"

def normalize(text):
    text = unicodedata.normalize("NFKD", text.casefold())
    return "".join(
        char for char in text
        if not unicodedata.combining(char)
    ).strip()

def kategori_bul(tags):
    if tags.get("leisure") == "park":
        return "doğa"
    if tags.get("tourism") == "viewpoint":
        return "doğa"
    return "tarih"

def adaylari_getir(lat, lon):
    sorgu = f"""
    [out:json][timeout:60];
    (
      nwr["tourism"~"^(museum|attraction|gallery|viewpoint)$"]
        (around:8000,{lat},{lon});
      nwr["historic"~"^(monument|castle|fort|archaeological_site)$"]
        (around:8000,{lat},{lon});
      nwr["leisure"="park"]
        (around:8000,{lat},{lon});
    );
    out center 350;
    """

    veri = urllib.parse.urlencode({"data": sorgu}).encode()

    istek = urllib.request.Request(
        API,
        data=veri,
        headers={"User-Agent": "VoyageAI-StudentProject/1.0"}
    )

    with urllib.request.urlopen(istek, timeout=100) as cevap:
        return json.load(cevap)["elements"]

def main():
    dosya = Path(__file__).parent / "yeni_yer_adaylari.csv"
    satirlar = []

    for sehir, (sehir_id, lat, lon, hedef) in SEHIRLER.items():
        print(f"{sehir} için adaylar aranıyor...")

        try:
            elemanlar = adaylari_getir(lat, lon)
        except Exception as hata:
            print(f"  API hatası: {hata}")
            continue

        gorulen = set()
        bulunan = 0

        for eleman in elemanlar:
            tags = eleman.get("tags", {})
            ad = tags.get("name:tr") or tags.get("name")

            if not ad:
                continue

            anahtar = normalize(ad)

            if anahtar in gorulen:
                continue

            konum = eleman.get("center", eleman)
            enlem = konum.get("lat")
            boylam = konum.get("lon")

            if enlem is None or boylam is None:
                continue

            gorulen.add(anahtar)

            satirlar.append({
                "sehir_id": sehir_id,
                "sehir": sehir,
                "ad": ad,
                "kategori": kategori_bul(tags),
                "enlem": enlem,
                "boylam": boylam,
                "ziyaret_suresi": "",
                "ortalama_ucret": "",
                "kaynak": (
                    f"https://www.openstreetmap.org/"
                    f"{eleman['type']}/{eleman['id']}"
                ),
                "durum": "inceleme_bekliyor"
            })

            bulunan += 1

            # Fazladan aday alıyoruz; mevcut yerlerle
            # tekrarları temizlemek gerekecek.
            if bulunan >= hedef + 20:
                break

        print(f"  {bulunan} aday bulundu.")
        time.sleep(2)

    alanlar = [
        "sehir_id", "sehir", "ad", "kategori",
        "enlem", "boylam", "ziyaret_suresi",
        "ortalama_ucret", "kaynak", "durum"
    ]

    with dosya.open("w", encoding="utf-8-sig", newline="") as f:
        yazici = csv.DictWriter(f, fieldnames=alanlar)
        yazici.writeheader()
        yazici.writerows(satirlar)

    print(f"\nCSV oluşturuldu: {dosya}")
    print(f"Toplam aday: {len(satirlar)}")
    print("Henüz veritabanına kayıt yapılmadı.")

if __name__ == "__main__":
    main()
