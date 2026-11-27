"""Tahmini fiyat kuralları (fiyat_tahmini.py)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fiyat_tahmini as ft  # noqa: E402


class FiyatTahminiTesti(unittest.TestCase):
    def test_mesafe(self):
        # İstanbul Havalimanı -> Paris merkezi yaklaşık 2.250 km
        km = ft.mesafe_km(41.2753, 28.7519, 48.8566, 2.3522)
        self.assertTrue(2150 < km < 2350, km)

    def test_ucus_mesafeyle_artar(self):
        self.assertLess(ft.ucus_tahmini(500, False), ft.ucus_tahmini(2500, False))
        # 1200 + 1,6 × 2000 = 4400
        self.assertEqual(ft.ucus_tahmini(2000, False), 4400)

    def test_ucus_en_az(self):
        self.assertEqual(ft.ucus_tahmini(0, True), ft.UCUS_EN_AZ_TL)

    def test_mesafe_yoksa_yedek(self):
        self.assertEqual(ft.ucus_tahmini(None, True), ft.UCUS_YEDEK_TL["yurt_ici"])
        self.assertEqual(ft.ucus_tahmini(None, False), ft.UCUS_YEDEK_TL["yurt_disi"])

    def test_ulke_seviyesi(self):
        self.assertGreater(ft.otel_tahmini("İsviçre"), ft.otel_tahmini("Fransa"))
        self.assertGreater(ft.otel_tahmini("Fransa"), ft.otel_tahmini("Mısır"))
        self.assertEqual(ft.otel_tahmini("Bilinmeyen Ülke"), ft.TABAN_OTEL_GECELIK_TL)
        self.assertEqual(ft.yemek_tahmini(None), ft.TABAN_YEMEK_GUNLUK_TL)


if __name__ == "__main__":
    unittest.main()
