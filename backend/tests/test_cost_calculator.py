"""Elle hesaplanan örnek: kod da aynı sonucu vermeli.

Çalıştırmak için backend klasöründe:
    python -m unittest discover tests
(pytest kuruluysa `pytest` da olur.)

ÖRNEK SEYAHAT (kâğıt üzerinde hesaplandı)
  3 kişi, 1-4 Aralık  -> 3 gece, 4 gün, 2 oda
  Gidiş 1.500 TL, dönüş 1.700 TL (kişi başı)
      uçuş      = (1500 + 1700) × 3          =  9.600
  Otel gecelik 2.000 TL
      konaklama = 2000 × 3 gece × 2 oda      = 12.000
  Günlük yemek 1.000 TL
      yemek     = 1000 × 4 gün × 3 kişi      = 12.000
  Günlük ulaşım 300 TL
      ulaşım    = 300 × 4 gün × 3 kişi       =  3.600
  Rotadaki yerler: 250, 0, (boş), 150 TL
      aktivite  = (250 + 0 + 0 + 150) × 3    =  1.200
                                     TOPLAM  = 38.400
"""

import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cost_calculator as cc  # noqa: E402


ORNEK = dict(
    gidis_kisi_basi_tl=1500,
    donus_kisi_basi_tl=1700,
    gecelik_fiyat_tl=2000,
    gunluk_yemek_tl=1000,
    gunluk_ulasim_tl=300,
    rotadaki_ucretler_tl=[250, 0, None, 150],
    start_date=date(2026, 12, 1),
    end_date=date(2026, 12, 4),
    people_count=3,
)


class MaliyetTesti(unittest.TestCase):
    def setUp(self):
        self.sonuc = cc.maliyet_hesapla(**ORNEK)

    def test_bes_parca_ayri_ayri(self):
        self.assertEqual(self.sonuc.flight_cost, 9600)
        self.assertEqual(self.sonuc.accommodation_cost, 12000)
        self.assertEqual(self.sonuc.food_cost, 12000)
        self.assertEqual(self.sonuc.local_transport_cost, 3600)
        self.assertEqual(self.sonuc.activity_cost, 1200)

    def test_toplam_parcalarin_toplami(self):
        self.assertEqual(self.sonuc.total_cost, 38400)
        parcalar = self.sonuc.sozluk()
        self.assertEqual(
            parcalar["total_cost"],
            sum(parcalar[k] for k in (
                "flight_cost", "accommodation_cost", "food_cost",
                "activity_cost", "local_transport_cost")),
        )

    def test_gece_gun_oda(self):
        self.assertEqual(cc.gece_sayisi(date(2026, 12, 1), date(2026, 12, 4)), 3)
        self.assertEqual(cc.gun_sayisi(date(2026, 12, 1), date(2026, 12, 4)), 4)
        self.assertEqual(cc.oda_sayisi(1), 1)
        self.assertEqual(cc.oda_sayisi(2), 1)
        self.assertEqual(cc.oda_sayisi(3), 2)
        self.assertEqual(cc.oda_sayisi(4), 2)

    def test_hatali_tarih(self):
        with self.assertRaises(ValueError):
            cc.gece_sayisi(date(2026, 12, 4), date(2026, 12, 4))

    def test_bos_gunluk_maliyette_varsayilan(self):
        self.assertEqual(
            cc.yemek_maliyeti(None, 2, 1), cc.VARSAYILAN_GUNLUK_YEMEK_TL * 2
        )
        self.assertEqual(
            cc.ulasim_maliyeti(None, 2, 1), cc.VARSAYILAN_GUNLUK_ULASIM_TL * 2
        )


class PuanTesti(unittest.TestCase):
    AGIRLIK = {"nature": 40, "food": 30, "history": 20, "nightlife": 10}
    SEHIR = {"nature": 80, "food": 60, "history": 50, "nightlife": 20}

    def test_tercih_puani(self):
        # (40×80 + 30×60 + 20×50 + 10×20) / 100 = 62
        self.assertEqual(cc.tercih_puani(self.AGIRLIK, self.SEHIR), 62)

    def test_agirlik_toplami_100_degilse_hata(self):
        with self.assertRaises(ValueError):
            cc.tercih_puani({**self.AGIRLIK, "food": 31}, self.SEHIR)

    def test_butce_icinde_100(self):
        self.assertEqual(cc.butce_uyum_puani(38400, 40000), 100)
        self.assertEqual(cc.butce_uyum_puani(40000, 40000), 100)

    def test_butce_asiminda_ceza(self):
        # 38.400 / 32.000 -> %20 aşım -> 100 - 20×2 = 60
        self.assertEqual(cc.butce_uyum_puani(38400, 32000), 60)
        # %60 aşım -> 100 - 120 -> 0'ın altına inmez
        self.assertEqual(cc.butce_uyum_puani(51200, 32000), 0)

    def test_genel_puan(self):
        # 62 × 0,6 + 60 × 0,4 = 37,2 + 24 = 61,2
        self.assertEqual(cc.genel_puan(62, 60), 61.2)

    def test_kategori_sayilarindan_puan(self):
        puan = cc.kategori_sayilarindan_puan(
            {"nature": 2, "food": 1, "history": 5, "nightlife": 2}
        )
        self.assertEqual(puan, {"nature": 20, "food": 10, "history": 50, "nightlife": 20})
        self.assertEqual(
            cc.kategori_sayilarindan_puan({}),
            {"nature": 0, "food": 0, "history": 0, "nightlife": 0},
        )


if __name__ == "__main__":
    unittest.main()
