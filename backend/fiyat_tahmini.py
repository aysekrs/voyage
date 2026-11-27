"""Gerçek uçuş/otel fiyatı ve şehrin günlük maliyeti yokken kullanılan
TAHMİNİ fiyatlar (prototip). Hepsi TL.

- Uçuş: kalkış havalimanı ile şehir merkezi arasındaki mesafeye göre.
- Otel, yemek, şehir içi ulaşım: ülkenin fiyat seviyesine göre.

Gerçek veri (kaydedilmiş uçuş/otel, şehrin günlük yemek maliyeti) varsa
her zaman o kullanılır; bu dosya sadece boşlukları doldurur.
"""
from math import atan2, cos, radians, sin, sqrt

# Uçuş (kişi başı, tek yön): sabit + km başına
UCUS_SABIT_TL = 1200
UCUS_KM_TL = 1.6
UCUS_EN_AZ_TL = 1200
# Mesafe hesaplanamazsa
UCUS_YEDEK_TL = {"yurt_ici": 1450, "yurt_disi": 4500}

# Ülke fiyat seviyesi 1.0 olan bir ülkede taban değerler
TABAN_OTEL_GECELIK_TL = 3000
TABAN_YEMEK_GUNLUK_TL = 1200
TABAN_ULASIM_GUNLUK_TL = 400

# Kaba göreli fiyat seviyeleri (1.0 = ortalama Avrupa şehri)
ULKE_SEVIYESI = {
    "Türkiye": 0.6,
    "Mısır": 0.4,
    "Portekiz": 0.85,
    "İspanya": 0.95,
    "İtalya": 1.05,
    "Almanya": 1.05,
    "Avusturya": 1.05,
    "Belçika": 1.1,
    "Fransa": 1.2,
    "Hollanda": 1.2,
    "İsviçre": 1.7,
}
VARSAYILAN_SEVIYE = 1.0


def mesafe_km(lat1, lon1, lat2, lon2) -> float:
    """İki nokta arası kuş uçuşu mesafe (Haversine)."""
    r = 6371.0
    p1, p2 = radians(lat1), radians(lat2)
    dp, dl = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * r * atan2(sqrt(a), sqrt(1 - a))


def ucus_tahmini(km: float | None, yurt_ici: bool) -> float:
    if km is None:
        return float(UCUS_YEDEK_TL["yurt_ici" if yurt_ici else "yurt_disi"])
    return float(round(max(UCUS_EN_AZ_TL, UCUS_SABIT_TL + UCUS_KM_TL * km), -1))


def ulke_seviyesi(ulke: str | None) -> float:
    return ULKE_SEVIYESI.get((ulke or "").strip(), VARSAYILAN_SEVIYE)


def otel_tahmini(ulke: str | None) -> float:
    return round(TABAN_OTEL_GECELIK_TL * ulke_seviyesi(ulke), -1)


def yemek_tahmini(ulke: str | None) -> float:
    return round(TABAN_YEMEK_GUNLUK_TL * ulke_seviyesi(ulke), -1)


def ulasim_tahmini(ulke: str | None) -> float:
    return round(TABAN_ULASIM_GUNLUK_TL * ulke_seviyesi(ulke), -1)
