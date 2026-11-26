"""havalimanlari.csv dosyasını OurAirports verisinden üretir (tek seferlik).

Kaynak: https://ourairports.com/data/ (airports.csv) - kamu malı (public domain).
Çalıştırma:
    python veri/havalimanlari_hazirla.py <indirilen airports.csv yolu>

Seçilenler: IATA kodu olan, tarifeli yolcu uçuşu yapılan (scheduled_service=yes)
büyük/orta/küçük havalimanları. Helikopter ve deniz uçağı pistleri alınmaz.
Ülke adları ulkeler.json'dan (Türkçe/İngilizce), sık kullanılan şehirlerin
Türkçe adları aşağıdaki sözlükten ve B'nin sehirler listesinden gelir.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

VERI = Path(__file__).resolve().parent
CIKTI = VERI / "havalimanlari.csv"
ALANLAR = ["iata", "name", "city", "city_tr", "country_code", "country", "country_tr",
           "lat", "lon", "type", "keywords"]

# OurAirports'ta ilçe adı yazan havalimanları -> bilinen şehir adı
TR_SEHIR = {
    "IST": "İstanbul", "SAW": "İstanbul", "ADB": "İzmir", "YEI": "Bursa", "COV": "Adana",
    "TEQ": "Tekirdağ", "KZR": "Kütahya", "HTY": "Hatay", "EDO": "Balıkesir", "GZP": "Alanya",
    "BJV": "Bodrum", "DLM": "Dalaman", "NAV": "Nevşehir", "CKZ": "Çanakkale",
    "ECN": "Lefkoşa",  # Ercan (KKTC)
}

# Sık aranan yabancı şehirlerin Türkçe adları (İngilizce ad -> Türkçe ad)
SEHIR_TR = {
    "London": "Londra", "Munich": "Münih", "Rome": "Roma", "Milan": "Milano", "Naples": "Napoli",
    "Venice": "Venedik", "Florence": "Floransa", "Athens": "Atina", "Thessaloniki": "Selanik",
    "Moscow": "Moskova", "Vienna": "Viyana", "Prague": "Prag", "Warsaw": "Varşova",
    "Copenhagen": "Kopenhag", "Brussels": "Brüksel", "Lisbon": "Lizbon", "Geneva": "Cenevre",
    "Zurich": "Zürih", "Cairo": "Kahire", "Alexandria": "İskenderiye", "Bucharest": "Bükreş",
    "Belgrade": "Belgrad", "Sarajevo": "Saraybosna", "Skopje": "Üsküp", "Tbilisi": "Tiflis",
    "Baku": "Bakü", "Kyiv": "Kiev", "Kiev": "Kiev", "Cologne": "Köln", "Nuremberg": "Nürnberg",
    "Marseille": "Marsilya", "Barcelona": "Barselona", "Seville": "Sevilla", "Valencia": "Valensiya",
    "Edinburgh": "Edinburg", "Stockholm": "Stokholm", "Budapest": "Budapeşte", "Sofia": "Sofya",
    "Chisinau": "Kişinev", "Krakow": "Krakov", "Kraków": "Krakov", "Beijing": "Pekin",
    "Shanghai": "Şanghay", "Seoul": "Seul", "Singapore": "Singapur", "Jakarta": "Cakarta",
    "New Delhi": "Yeni Delhi", "Abu Dhabi": "Abu Dabi", "Riyadh": "Riyad", "Jeddah": "Cidde",
    "Medina": "Medine", "Tehran": "Tahran", "Baghdad": "Bağdat", "Beirut": "Beyrut",
    "Tunis": "Tunus", "Algiers": "Cezayir", "Casablanca": "Kazablanka", "Marrakesh": "Marakeş",
    "Luxembourg": "Lüksemburg", "Nicosia": "Lefkoşa", "Hamburg": "Hamburg", "Basel": "Basel",
    "Lyon": "Lyon", "Nice": "Nice", "The Hague": "Lahey", "Antwerp": "Anvers", "Porto": "Porto",
    "Malaga": "Malaga", "Málaga": "Malaga", "Palma de Mallorca": "Palma", "Tirana": "Tiran",
    "Podgorica": "Podgoritsa", "Ljubljana": "Ljubljana", "Zagreb": "Zagreb", "Split": "Split",
    "Dubrovnik": "Dubrovnik", "Minsk": "Minsk", "Riga": "Riga", "Tallinn": "Tallinn",
    "Vilnius": "Vilnius", "Helsinki": "Helsinki", "Oslo": "Oslo", "Reykjavik": "Reykjavik",
    "Tashkent": "Taşkent", "Almaty": "Almatı", "Astana": "Astana", "Bishkek": "Bişkek",
    "Ashgabat": "Aşkabat", "Yerevan": "Erivan", "Damascus": "Şam", "Amman": "Amman",
    "Tel Aviv": "Tel Aviv", "Doha": "Doha", "Kuwait City": "Kuveyt", "Muscat": "Maskat",
    "Tokyo": "Tokyo", "Osaka": "Osaka", "Bangkok": "Bangkok", "Kuala Lumpur": "Kuala Lumpur",
    "New York": "New York", "Washington": "Washington", "Los Angeles": "Los Angeles",
    "Mexico City": "Meksiko", "Sao Paulo": "São Paulo", "Rio de Janeiro": "Rio de Janeiro",
}


def sehir_adi(satir: dict) -> str:
    belediye = (satir.get("municipality") or "").strip()
    belediye = belediye.split("(")[0].split(",")[0].strip()
    return belediye or satir.get("name", "")


def main(kaynak: Path) -> None:
    ulkeler = json.loads((VERI / "ulkeler.json").read_text(encoding="utf-8"))

    # B'nin şehir listesi: havalimanı kodu -> Türkçe şehir adı (Roma, Viyana, Münih...)
    b_sehirleri = {}
    b_csv = VERI.parent.parent / "kisi-b-kodlari" / "backend" / "voyageai_sehirler.csv"
    if b_csv.is_file():
        for s in csv.DictReader(b_csv.open(encoding="utf-8-sig")):
            if s.get("havalimani_kodu", "").strip():
                b_sehirleri[s["havalimani_kodu"].strip()] = s["ad"].strip()

    satirlar = []
    with kaynak.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            kod = r["iata_code"].strip().upper()
            if (len(kod) != 3 or r["scheduled_service"] != "yes"
                    or r["type"] not in ("large_airport", "medium_airport", "small_airport")):
                continue
            ulke = ulkeler.get(r["iso_country"], {})
            sehir = TR_SEHIR.get(kod) or sehir_adi(r)
            sehir_tr = TR_SEHIR.get(kod) or b_sehirleri.get(kod) or SEHIR_TR.get(sehir) or ""
            satirlar.append({
                "iata": kod,
                "name": r["name"].strip(),
                "city": sehir,
                "city_tr": sehir_tr if sehir_tr != sehir else "",
                "country_code": r["iso_country"],
                "country": ulke.get("en", r["iso_country"]),
                "country_tr": ulke.get("tr", ""),
                "lat": round(float(r["latitude_deg"]), 5),
                "lon": round(float(r["longitude_deg"]), 5),
                "type": r["type"].replace("_airport", ""),
                "keywords": r.get("keywords", "").strip()[:200],
            })

    # Aynı IATA kodu iki kez geçerse büyük olanı tut
    sira = {"large": 0, "medium": 1, "small": 2}
    tekil: dict[str, dict] = {}
    for s in sorted(satirlar, key=lambda s: sira[s["type"]]):
        tekil.setdefault(s["iata"], s)

    with CIKTI.open("w", encoding="utf-8", newline="") as f:
        yazici = csv.DictWriter(f, fieldnames=ALANLAR)
        yazici.writeheader()
        yazici.writerows(sorted(tekil.values(), key=lambda s: s["iata"]))
    print(f"{len(tekil)} havalimanı yazıldı: {CIKTI}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Kullanım: python veri/havalimanlari_hazirla.py <airports.csv>")
    main(Path(sys.argv[1]))
