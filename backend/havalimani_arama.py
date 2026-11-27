"""Havalimanı arama yardımcıları (veritabanına bağlanmaz, testlenebilir).

Arama Türkçe karakter ve aksan duyarsızdır: "munih", "Münih", "MUNICH",
"istanbul", "İstanbul" hepsi aynı sonucu bulur.
"""
from __future__ import annotations

import re
import unicodedata

_TR = str.maketrans({"İ": "i", "I": "i", "ı": "i", "ğ": "g", "Ğ": "g", "ş": "s", "Ş": "s",
                     "ç": "c", "Ç": "c", "ö": "o", "Ö": "o", "ü": "u", "Ü": "u"})


def normalize(metin: str | None) -> str:
    """Küçük harf, Türkçe harfler ve aksanlar sadeleşmiş, tek boşluklu metin."""
    if not metin:
        return ""
    metin = str(metin).translate(_TR)
    metin = unicodedata.normalize("NFKD", metin)
    metin = "".join(c for c in metin if not unicodedata.combining(c))
    metin = re.sub(r"[^\w]+", " ", metin.lower())
    return re.sub(r"\s+", " ", metin).strip()


def arama_metni(satir: dict) -> str:
    """Bir havalimanının aranabilir bütün adları tek metinde."""
    parcalar = [
        satir.get("iata"), satir.get("city_tr"), satir.get("city"), satir.get("name"),
        satir.get("country_tr"), satir.get("country"), (satir.get("keywords") or "")[:200],
    ]
    return " " + normalize(" ".join(p for p in parcalar if p)) + " "


def gorunen_ad(satir: dict) -> str:
    """Listede gösterilecek metin: "Roma – Fiumicino ... (FCO), İtalya"."""
    sehir = satir.get("city_tr") or satir.get("city") or ""
    ulke = satir.get("country_tr") or satir.get("country") or ""
    return f"{sehir} – {satir.get('name')} ({satir.get('iata')}), {ulke}"


# Birden çok havalimanı olan şehirlerde asistanın varsayılan seçtiği ana havalimanı
ANA_HAVALIMANI = {
    "istanbul": "IST", "londra": "LHR", "london": "LHR", "paris": "CDG", "roma": "FCO",
    "rome": "FCO", "milano": "MXP", "milan": "MXP", "moskova": "SVO", "moscow": "SVO",
    "new york": "JFK", "berlin": "BER", "stokholm": "ARN", "stockholm": "ARN",
    "tokyo": "HND", "bukres": "OTP", "bucharest": "OTP", "brüksel": "BRU", "bruksel": "BRU",
    "brussels": "BRU", "oslo": "OSL", "washington": "IAD", "dubai": "DXB", "ankara": "ESB",
    "antalya": "AYT", "izmir": "ADB",
}


def kalkis_sozlugu_olustur(satirlar: list[dict]) -> dict[str, tuple[str, str]]:
    """{normalize(şehir adı): (gösterilecek şehir adı, IATA)}.

    satirlar: airports tablosundan iata, city, city_tr, type içeren kayıtlar.
    Aynı şehirde birden çok havalimanı varsa ANA_HAVALIMANI, yoksa en büyüğü seçilir.
    """
    sira = {"large": 0, "medium": 1, "small": 2}
    sozluk: dict[str, tuple[str, str, int]] = {}
    for s in satirlar:
        gorunen = s.get("city_tr") or s["city"]
        for ad in {s.get("city_tr"), s["city"]}:
            anahtar = normalize(ad)
            if not anahtar:
                continue
            if ANA_HAVALIMANI.get(anahtar) == s["iata"]:
                puan = -1
            else:
                puan = sira.get(s.get("type"), 3)
            onceki = sozluk.get(anahtar)
            if onceki is None or puan < onceki[2]:
                sozluk[anahtar] = (gorunen, s["iata"], puan)
    return {k: (v[0], v[1]) for k, v in sozluk.items()}
