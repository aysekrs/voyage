"""5. Hafta: maliyet ve skor hesabı.

Bu dosyada veritabanı ya da internet yok, sadece hesap var.
Böylece her formül elle hesaplanan örneklerle test edilebilir
(bkz. tests/test_cost_calculator.py).

Tüm tutarlar TL'dir. Döviz çevirisi bu fonksiyonlara gelmeden
önce yapılır.
"""

from dataclasses import dataclass, asdict
from math import ceil

# ---------------------------------------------------------------
# Ekipçe belirlenen sabitler (değiştirmek gerekirse sadece burası)
# ---------------------------------------------------------------

# Genel puan = tercih puanı × TERCIH_ORANI + bütçe uyumu × BUTCE_ORANI
TERCIH_ORANI = 0.6
BUTCE_ORANI = 0.4

# Bütçe aşıldığında her %1 aşım için düşülen puan
BUTCE_ASIM_CEZASI = 2

# Bir odada kalan kişi sayısı (oda = kişi / 2, yukarı yuvarlanır)
ODA_BASI_KISI = 2

# Şehrin verisi boşsa kullanılan varsayılan günlük maliyetler (kişi başı, TL)
VARSAYILAN_GUNLUK_YEMEK_TL = 1200
VARSAYILAN_GUNLUK_ULASIM_TL = 400

ILGI_ALANLARI = ("nature", "food", "history", "nightlife")


@dataclass
class MaliyetDokumu:
    flight_cost: float
    accommodation_cost: float
    food_cost: float
    activity_cost: float
    local_transport_cost: float

    @property
    def total_cost(self) -> float:
        return round(
            self.flight_cost
            + self.accommodation_cost
            + self.food_cost
            + self.activity_cost
            + self.local_transport_cost,
            2,
        )

    def sozluk(self) -> dict:
        veri = asdict(self)
        veri["total_cost"] = self.total_cost
        return veri


# ---------------------------------------------------------------
# Süre ve oda
# ---------------------------------------------------------------

def gece_sayisi(start_date, end_date) -> int:
    gece = (end_date - start_date).days
    if gece < 1:
        raise ValueError("Bitiş tarihi başlangıçtan sonra olmalıdır.")
    return gece


def gun_sayisi(start_date, end_date) -> int:
    """1-4 Aralık: 3 gece, 4 gün."""
    return gece_sayisi(start_date, end_date) + 1


def oda_sayisi(people_count: int) -> int:
    if people_count < 1:
        raise ValueError("Kişi sayısı en az 1 olmalıdır.")
    return ceil(people_count / ODA_BASI_KISI)


# ---------------------------------------------------------------
# Beş maliyet parçası
# ---------------------------------------------------------------

def ucus_maliyeti(gidis_kisi_basi_tl: float, donus_kisi_basi_tl: float,
                  people_count: int) -> float:
    return round((gidis_kisi_basi_tl + donus_kisi_basi_tl) * people_count, 2)


def konaklama_maliyeti(gecelik_fiyat_tl: float, gece: int,
                       people_count: int) -> float:
    return round(gecelik_fiyat_tl * gece * oda_sayisi(people_count), 2)


def yemek_maliyeti(gunluk_yemek_tl: float | None, gun: int,
                   people_count: int) -> float:
    if gunluk_yemek_tl is None:
        gunluk_yemek_tl = VARSAYILAN_GUNLUK_YEMEK_TL
    return round(gunluk_yemek_tl * gun * people_count, 2)


def ulasim_maliyeti(gunluk_ulasim_tl: float | None, gun: int,
                    people_count: int) -> float:
    if gunluk_ulasim_tl is None:
        gunluk_ulasim_tl = VARSAYILAN_GUNLUK_ULASIM_TL
    return round(gunluk_ulasim_tl * gun * people_count, 2)


def aktivite_maliyeti(rotadaki_ucretler_tl: list, people_count: int) -> float:
    """Rotadaki yerlerin ortalama ücretlerinin toplamı × kişi sayısı.
    Ücreti boş olan yer ücretsiz sayılır."""
    toplam = sum(ucret or 0 for ucret in rotadaki_ucretler_tl)
    return round(toplam * people_count, 2)


def maliyet_hesapla(*, gidis_kisi_basi_tl, donus_kisi_basi_tl,
                    gecelik_fiyat_tl, gunluk_yemek_tl, gunluk_ulasim_tl,
                    rotadaki_ucretler_tl, start_date, end_date,
                    people_count) -> MaliyetDokumu:
    gece = gece_sayisi(start_date, end_date)
    gun = gun_sayisi(start_date, end_date)
    return MaliyetDokumu(
        flight_cost=ucus_maliyeti(gidis_kisi_basi_tl, donus_kisi_basi_tl, people_count),
        accommodation_cost=konaklama_maliyeti(gecelik_fiyat_tl, gece, people_count),
        food_cost=yemek_maliyeti(gunluk_yemek_tl, gun, people_count),
        activity_cost=aktivite_maliyeti(rotadaki_ucretler_tl, people_count),
        local_transport_cost=ulasim_maliyeti(gunluk_ulasim_tl, gun, people_count),
    )


# ---------------------------------------------------------------
# Puanlar (hepsi 0-100 arası)
# ---------------------------------------------------------------

def tercih_puani(agirliklar: dict, sehir_puanlari: dict) -> float:
    """Ağırlıklı toplam. Ağırlıkların toplamı 100, şehir puanları 0-100.
    Örn: doğa 40 × 80 + yemek 30 × 60 + tarih 20 × 50 + gece 10 × 20
         = (3200 + 1800 + 1000 + 200) / 100 = 62"""
    toplam_agirlik = sum(agirliklar[alan] for alan in ILGI_ALANLARI)
    if toplam_agirlik != 100:
        raise ValueError("Dört ilgi ağırlığının toplamı 100 olmalıdır.")
    toplam = sum(
        agirliklar[alan] * (sehir_puanlari.get(alan) or 0)
        for alan in ILGI_ALANLARI
    )
    return round(toplam / 100, 1)


def kategori_sayilarindan_puan(sayilar: dict) -> dict:
    """Şehrin 4 puanı veritabanında boşsa yer kategorilerinden üretilir:
    her alanın puanı = o kategorideki yer sayısı / toplam yer × 100."""
    toplam = sum(sayilar.get(alan, 0) for alan in ILGI_ALANLARI)
    if toplam == 0:
        return {alan: 0.0 for alan in ILGI_ALANLARI}
    return {
        alan: round(sayilar.get(alan, 0) / toplam * 100, 1)
        for alan in ILGI_ALANLARI
    }


def butce_uyum_puani(total_cost: float, budget_try: float) -> float:
    """Bütçe içindeyse 100. Aşarsa her %1 aşım için BUTCE_ASIM_CEZASI puan düşer."""
    if budget_try <= 0:
        raise ValueError("Bütçe 0'dan büyük olmalıdır.")
    if total_cost <= budget_try:
        return 100.0
    asim_yuzde = (total_cost - budget_try) / budget_try * 100
    return round(max(0.0, 100 - asim_yuzde * BUTCE_ASIM_CEZASI), 1)


def genel_puan(tercih: float, butce_uyumu: float) -> float:
    return round(tercih * TERCIH_ORANI + butce_uyumu * BUTCE_ORANI, 1)
