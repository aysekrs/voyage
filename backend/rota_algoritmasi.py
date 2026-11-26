
from math import radians, sin, cos, sqrt, atan2


# 1. Haversine: iki koordinat arasındaki kuş uçuşu mesafe
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1))
        * cos(radians(lat2))
        * sin(dlon / 2) ** 2
    )

    return 2 * R * atan2(sqrt(a), sqrt(max(0, 1 - a)))


def mesafe(yer1, yer2):
    return haversine(
        yer1["lat"], yer1["lon"],
        yer2["lat"], yer2["lon"]
    )


# 2. Bir rotanın toplam kuş uçuşu mesafesi
def rota_mesafesi(rota):
    return sum(
        mesafe(rota[i], rota[i + 1])
        for i in range(len(rota) - 1)
    )


# 3. Nearest Neighbor: en yakın sonraki yeri seç
def nearest_neighbor(yerler):
    if not yerler:
        return []

    kalan = yerler[1:].copy()
    rota = [yerler[0]]

    while kalan:
        son_yer = rota[-1]

        en_yakin = min(
            kalan,
            key=lambda y: mesafe(son_yer, y)
        )

        rota.append(en_yakin)
        kalan.remove(en_yakin)

    return rota


# 4. 2-opt: rota sırasını iyileştir
def two_opt(rota):
    en_iyi = rota.copy()

    if len(en_iyi) < 4:
        return en_iyi

    iyilesti = True

    while iyilesti:
        iyilesti = False

        for i in range(1, len(en_iyi) - 2):
            for j in range(i + 1, len(en_iyi)):
                aday = (
                    en_iyi[:i]
                    + en_iyi[i:j][::-1]
                    + en_iyi[j:]
                )

                if (
                    rota_mesafesi(aday)
                    < rota_mesafesi(en_iyi) - 1e-9
                ):
                    en_iyi = aday
                    iyilesti = True
                    break

            if iyilesti:
                break

    return en_iyi


def rota_olustur(yerler):
    if not yerler:
        return {
            "rota": [],
            "ilk_mesafe_km": 0,
            "son_mesafe_km": 0
        }

    ilk_rota = nearest_neighbor(yerler)
    optimize_rota = two_opt(ilk_rota)

    ilk_mesafe = rota_mesafesi(ilk_rota)
    son_mesafe = rota_mesafesi(optimize_rota)

    assert son_mesafe <= ilk_mesafe + 1e-8

    return {
        "rota": optimize_rota,
        "ilk_mesafe_km": round(ilk_mesafe, 3),
        "son_mesafe_km": round(son_mesafe, 3)
    }


if __name__ == "__main__":
    # Algoritma testi için örnek koordinatlar
    # Gerçek veritabanı koordinatları değildir.
    test_yerleri = [
        {"id": 1, "ad": "A", "lat": 41.00, "lon": 29.00},
        {"id": 2, "ad": "B", "lat": 41.02, "lon": 29.04},
        {"id": 3, "ad": "C", "lat": 41.05, "lon": 29.01},
        {"id": 4, "ad": "D", "lat": 41.01, "lon": 29.08},
        {"id": 5, "ad": "E", "lat": 41.07, "lon": 29.06}
    ]

    sonuc = rota_olustur(test_yerleri)

    print("\nVOYAGEAI ROTA ALGORITMASI")
    print("------------------------")

    print("Rota sirasi:")
    for sira, yer in enumerate(sonuc["rota"], 1):
        print(f"{sira}. {yer['ad']}")

    print("Nearest Neighbor mesafesi:",
          sonuc["ilk_mesafe_km"], "km")

    print("2-opt mesafesi:",
          sonuc["son_mesafe_km"], "km")

    print("TEST BASARILI: 2-opt mesafeyi artirmadi.")
