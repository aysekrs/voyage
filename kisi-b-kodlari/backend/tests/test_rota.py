"""VoyageAI rota algoritması testleri (hafta 3).

Çalıştırma (backend klasöründe):  python -m pytest tests -v
Veritabanı gerekmez.
"""
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rota_algoritmasi import haversine, nearest_neighbor, rota_mesafesi, rota_olustur, two_opt  # noqa: E402
from rota_planlayici import gun_toplam_dk, gunlere_bol, yol_suresi_dk  # noqa: E402


def rastgele_yerler(n, tohum, merkez=(41.01, 28.98), yayilim=0.08):
    r = random.Random(tohum)
    return [
        {
            "id": i,
            "ad": f"Yer {i}",
            "lat": merkez[0] + r.uniform(-yayilim, yayilim),
            "lon": merkez[1] + r.uniform(-yayilim, yayilim),
            "ziyaret_suresi": r.choice([30, 45, 60, 90, 120]),
        }
        for i in range(1, n + 1)
    ]


# ---------- Haversine ----------

def test_haversine_ayni_nokta_sifir():
    assert haversine(41.0, 29.0, 41.0, 29.0) == 0


def test_haversine_bilinen_mesafe_istanbul_ankara():
    # Sultanahmet - Kızılay kuş uçuşu ~350 km
    km = haversine(41.0054, 28.9768, 39.9208, 32.8541)
    assert 345 < km < 355


def test_haversine_simetrik():
    assert haversine(48.85, 2.35, 52.52, 13.40) == pytest.approx(haversine(52.52, 13.40, 48.85, 2.35))


# ---------- Nearest Neighbor ----------

def test_nn_bos_liste():
    assert nearest_neighbor([]) == []


@pytest.mark.parametrize("tohum", range(5))
def test_nn_her_yeri_bir_kez_ziyaret_eder(tohum):
    yerler = rastgele_yerler(15, tohum)
    rota = nearest_neighbor(yerler)
    assert sorted(y["id"] for y in rota) == sorted(y["id"] for y in yerler)
    assert rota[0]["id"] == yerler[0]["id"]


def test_nn_dogru_cizgide_sirali_gider():
    yerler = [{"id": i, "lat": 41.0, "lon": 29.0 + d} for i, d in enumerate([0, 0.03, 0.01, 0.02])]
    assert [y["id"] for y in nearest_neighbor(yerler)] == [0, 2, 3, 1]


# ---------- 2-opt ----------

@pytest.mark.parametrize("tohum", range(30))
def test_2opt_mesafeyi_artirmaz(tohum):
    yerler = rastgele_yerler(12, tohum)
    nn = nearest_neighbor(yerler)
    assert rota_mesafesi(two_opt(nn)) <= rota_mesafesi(nn) + 1e-9


def test_2opt_capraz_rotayi_duzeltir():
    # Kare köşeleri çapraz sırada: 0-2-1-3 kesişir, 2-opt bunu açmalı.
    kare = [
        {"id": 0, "lat": 41.00, "lon": 29.00},
        {"id": 2, "lat": 41.01, "lon": 29.01},
        {"id": 1, "lat": 41.00, "lon": 29.01},
        {"id": 3, "lat": 41.01, "lon": 29.00},
    ]
    assert rota_mesafesi(two_opt(kare)) < rota_mesafesi(kare)


def test_rota_olustur_rapor_alanlari():
    sonuc = rota_olustur(rastgele_yerler(8, 1))
    assert sonuc["son_mesafe_km"] <= sonuc["ilk_mesafe_km"]
    assert len(sonuc["rota"]) == 8


# ---------- Yol süresi ----------

def test_yol_suresi_sifir_mesafe():
    assert yol_suresi_dk(0) == 0


def test_yol_suresi_mesafeyle_azalmaz():
    onceki = 0
    for km in [0.1, 0.5, 1.0, 1.5, 1.6, 3, 5, 10, 20]:
        dk = yol_suresi_dk(km)
        assert dk >= onceki
        onceki = dk


def test_kisa_mesafe_yurume_suresi_makul():
    # 1 km kuş uçuşu ≈ 1.3 km yürüyüş ≈ 17 dk
    assert 15 <= yol_suresi_dk(1.0) <= 20


# ---------- Günlere bölme ----------

@pytest.mark.parametrize("tohum", range(10))
@pytest.mark.parametrize("gun_sayisi,saat", [(1, 4), (3, 5), (5, 8)])
def test_gunlere_bol_kurallari(tohum, gun_sayisi, saat):
    yerler = rastgele_yerler(25, tohum)
    limit = saat * 60
    gunler, sigmayanlar = gunlere_bol(yerler, gun_sayisi, limit)

    # 1) İstenen kadar gün döner
    assert len(gunler) == gun_sayisi
    # 2) Her gün süre limitine (ziyaret + yol) uyar
    for gun in gunler:
        assert gun_toplam_dk(gun) <= limit
    # 3) Hiçbir yer kaybolmaz ya da iki kez kullanılmaz
    plandakiler = [y["id"] for gun in gunler for y in gun]
    assert len(plandakiler) == len(set(plandakiler))
    assert sorted(plandakiler + [y["id"] for y in sigmayanlar]) == sorted(y["id"] for y in yerler)


def test_gunlere_bol_her_sey_sigarsa_disarida_kalan_yok():
    yerler = rastgele_yerler(4, 3, yayilim=0.005)
    for y in yerler:
        y["ziyaret_suresi"] = 30
    gunler, sigmayanlar = gunlere_bol(yerler, 2, 8 * 60)
    assert sigmayanlar == []
    assert sum(len(g) for g in gunler) == 4


def test_gunlere_bol_cok_uzun_ziyaret_disarida_kalir():
    yerler = rastgele_yerler(3, 4)
    yerler[0]["ziyaret_suresi"] = 600
    _, sigmayanlar = gunlere_bol(yerler, 3, 5 * 60)
    assert yerler[0]["id"] in [y["id"] for y in sigmayanlar]


def test_gunlere_bol_bos_girdi():
    gunler, sigmayanlar = gunlere_bol([], 3, 300)
    assert gunler == [[], [], []] and sigmayanlar == []


def test_gunler_bolgesel_kalir():
    """İki uzak kümeden yerler: aynı gün iki kümeye birden düşmemeli."""
    batı = rastgele_yerler(5, 10, merkez=(41.00, 28.90), yayilim=0.005)
    doğu = rastgele_yerler(5, 11, merkez=(41.00, 29.10), yayilim=0.005)
    for i, y in enumerate(doğu):
        y["id"] = 100 + i
    yerler = []
    for a, b in zip(batı, doğu):  # karışık sırada ver
        yerler += [a, b]
    for y in yerler:
        y["ziyaret_suresi"] = 30
    gunler, _ = gunlere_bol(yerler, 2, 4 * 60)
    for gun in gunler:
        kumeler = {y["id"] >= 100 for y in gun}
        assert len(kumeler) <= 1


def test_her_sey_sigarsa_gunler_dengeli_dolar():
    """Süre bolken ilk günler dolup son günler boş kalmamalı."""
    yerler = rastgele_yerler(14, 7, yayilim=0.03)
    gunler, sigmayanlar = gunlere_bol(yerler, 7, 12 * 60)
    assert sigmayanlar == []
    assert all(len(gun) > 0 for gun in gunler)
