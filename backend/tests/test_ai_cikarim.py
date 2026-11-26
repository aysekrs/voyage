"""AI çıkarım testleri (5. hafta). Çalıştırma: python -m pytest tests -v (backend klasöründe)."""
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_cikarim import (  # noqa: E402
    AGIRLIKLAR, agirliklari_yuvarla, baslik_uret, birlestir, cikar, dogrula,
    kural_tabanli_cikar, yanit_uret,
)

BUGUN = date(2026, 11, 26)


def c(metin):
    return kural_tabanli_cikar(metin, BUGUN)


# ---------- tam cümle ----------

def test_tam_cumle():
    b = c("İzmir'den 2 kişi 15-20 Temmuz arası 40 bin TL bütçeyle tarih ve yemek ağırlıklı bir tatil")
    assert b["origin_city"] == "İzmir" and b["origin_airport_code"] == "ADB"
    assert b["people_count"] == 2
    assert b["budget_try"] == 40000
    assert b["start_date"] == "2027-07-15" and b["end_date"] == "2027-07-20"
    assert sum(b[a] for a in AGIRLIKLAR) == 100
    assert b["history_weight"] > b["nature_weight"]
    assert b["food_weight"] > b["nightlife_weight"]


# ---------- tek tek alanlar ----------

@pytest.mark.parametrize("metin,beklenen", [
    ("Ankara'dan çıkacağız", "Ankara"),
    ("istanbuldan gidiyoruz", "İstanbul"),
    ("Antalya çıkışlı olsun", "Antalya"),
])
def test_kalkis_sehri(metin, beklenen):
    assert c(metin)["origin_city"] == beklenen


def test_varis_sehri_kalkis_sanilmaz():
    assert "origin_city" not in c("Antalya'ya gitmek istiyorum")


def test_havalimani_kodu_dogrudan():
    assert c("SAW'dan uçalım")["origin_airport_code"] == "SAW"


@pytest.mark.parametrize("metin,tutar", [
    ("40 bin TL", 40000), ("40.000 TL", 40000), ("bütçem 25 bin", 25000),
    ("30k", 30000), ("12500 lira", 12500), ("7,5 bin tl", 7500),
])
def test_butce(metin, tutar):
    assert c(metin)["budget_try"] == tutar


@pytest.mark.parametrize("metin,kisi", [
    ("3 kişiyiz", 3), ("iki kişi", 2), ("tek başıma", 1), ("eşimle gideceğim", 2),
])
def test_kisi(metin, kisi):
    assert c(metin)["people_count"] == kisi


def test_tarih_iki_ay():
    b = c("28 Haziran - 3 Temmuz")
    assert (b["start_date"], b["end_date"]) == ("2027-06-28", "2027-07-03")


def test_tarih_yil_donumu():
    b = c("28 Aralık'tan 2 Ocak'a")
    assert (b["start_date"], b["end_date"]) == ("2026-12-28", "2027-01-02")


def test_tarih_noktali():
    b = c("15.03.2027 - 19.03.2027")
    assert (b["start_date"], b["end_date"]) == ("2027-03-15", "2027-03-19")


def test_tarih_gece_sayisi():
    b = c("10 Mayıs'ta 4 gece")
    assert (b["start_date"], b["end_date"]) == ("2027-05-10", "2027-05-14")


def test_gece_hayati_istemiyor():
    b = c("doğa ve deniz olsun, gece hayatı istemiyorum")
    assert b["nightlife_weight"] == 0
    assert b["nature_weight"] > b["food_weight"]


def test_ilgi_yoksa_agirlik_yok():
    assert "nature_weight" not in c("İzmir'den 2 kişi")


# ---------- yuvarlama ----------

@pytest.mark.parametrize("puan", [
    {"nature_weight": 1, "food_weight": 1, "history_weight": 1, "nightlife_weight": 0},
    {"nature_weight": 3, "food_weight": 1, "history_weight": 1, "nightlife_weight": 1},
    {"nature_weight": 7, "food_weight": 2, "history_weight": 9, "nightlife_weight": 1},
])
def test_agirliklar_100_ve_5in_kati(puan):
    s = agirliklari_yuvarla(puan)
    assert sum(s.values()) == 100 and all(v % 5 == 0 for v in s.values())


# ---------- birleştirme / sohbet ----------

def test_sonraki_mesaj_eksikleri_tamamlar():
    bilgi, _ = cikar(["İzmir'den 15-20 Temmuz", "2 kişiyiz, bütçe 30 bin TL", "doğa ve yemek"], BUGUN)
    temiz, eksik, hatalar = dogrula(bilgi, BUGUN)
    assert eksik == [] and hatalar == []
    assert temiz["people_count"] == 2 and temiz["budget_try"] == 30000


def test_duzeltme_eskisinin_ustune_yazar():
    bilgi, _ = cikar(["Ankara'dan 2 kişi", "aslında 3 kişiyiz"], BUGUN)
    assert bilgi["people_count"] == 3


def test_birlestir_bos_deger_silmez():
    assert birlestir({"people_count": 2}, {"people_count": None}) == {"people_count": 2}


# ---------- doğrulama ----------

def test_eksikler_sorulur():
    _, eksik, _ = dogrula({"origin_city": "İzmir"}, BUGUN)
    assert set(eksik) == {"budget_try", "people_count", "start_date", "end_date", "interests"}
    yanit = yanit_uret(eksik, [])
    assert "?" in yanit


def test_gecmis_tarih_hata():
    tam = {"origin_city": "İzmir", "budget_try": 1, "people_count": 1,
           "start_date": "2026-01-01", "end_date": "2026-01-05",
           "nature_weight": 25, "food_weight": 25, "history_weight": 25, "nightlife_weight": 25}
    _, _, hatalar = dogrula(tam, BUGUN)
    assert any("geçmiş" in h for h in hatalar)


def test_ters_tarih_hata():
    tam = {"origin_city": "İzmir", "budget_try": 1, "people_count": 1,
           "start_date": "2027-02-10", "end_date": "2027-02-05",
           "nature_weight": 25, "food_weight": 25, "history_weight": 25, "nightlife_weight": 25}
    _, _, hatalar = dogrula(tam, BUGUN)
    assert hatalar


def test_kucuk_harf_sehir_ve_kod_tamamlanir():
    temiz, eksik, _ = dogrula({"origin_city": "izmir"}, BUGUN)
    assert temiz["origin_city"] == "İzmir" and temiz["origin_airport_code"] == "ADB"
    assert "origin_airport_code" not in eksik


def test_bilinmeyen_sehirde_kod_sorulur():
    _, eksik, _ = dogrula({"origin_city": "Çanakkale"}, BUGUN)
    assert "origin_airport_code" in eksik


def test_llm_yoksa_kural_kullanilir(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    _, kaynak = cikar(["İzmir'den"], BUGUN)
    assert kaynak == "kural"


def test_baslik():
    assert baslik_uret({"origin_city": "İzmir", "start_date": "2027-07-15", "end_date": "2027-07-20"}) \
        == "İzmir çıkışlı seyahat (15.07–20.07.2027)"


def test_onay_kartinda_bos_kod_sehirden_dolar():
    temiz, eksik, _ = dogrula({"origin_city": "Ankara", "origin_airport_code": None}, BUGUN)
    assert temiz["origin_airport_code"] == "ESB" and "origin_airport_code" not in eksik


# ---------- gidilecek şehir ----------

SEHIRLER = ["Paris", "Roma", "Viyana", "İzmir", "Antalya", "Ebu Simbel", "Lizbon"]


@pytest.mark.parametrize("metin,sehir", [
    ("İzmir'den Paris'e gitmek istiyoruz", "Paris"),
    ("Roma'ya 3 kişi", "Roma"),
    ("viyanada 4 gece", "Viyana"),
    ("Lizbon gezisi planlıyorum", "Lizbon"),
    ("İstanbul'dan Antalya'ya", "Antalya"),
    ("Ebu Simbel'e tur", "Ebu Simbel"),
])
def test_varis(metin, sehir):
    assert kural_tabanli_cikar(metin, BUGUN, SEHIRLER)["destination"] == sehir


def test_kalkis_varis_sayilmaz():
    assert "destination" not in kural_tabanli_cikar("İzmir'den 2 kişi", BUGUN, SEHIRLER)


def test_varis_yoksa_bos():
    assert "destination" not in kural_tabanli_cikar("tatile gitmek istiyorum", BUGUN, SEHIRLER)


def test_listede_olmayan_varis_engellemez():
    temiz, _, hatalar = dogrula({"destination": "Tokyo"}, BUGUN, SEHIRLER)
    assert temiz["destination"] is None and "Tokyo" in temiz["varis_notu"] and not hatalar


def test_varis_buyuk_kucuk_harf_duzelir():
    temiz, _, _ = dogrula({"destination": "paris"}, BUGUN, SEHIRLER)
    assert temiz["destination"] == "Paris"


def test_varisli_baslik():
    assert baslik_uret({"origin_city": "İzmir", "destination": "Roma"}) == "İzmir → Roma seyahati"


def test_eksiz_varis():
    b = kural_tabanli_cikar("İzmir'den Roma 3 kişi 12-16 Aralık", BUGUN, SEHIRLER)
    assert b["destination"] == "Roma" and b["origin_city"] == "İzmir"


def test_eksiz_kalkis_varis_sayilmaz():
    assert "destination" not in kural_tabanli_cikar("İzmir çıkışlı 2 kişi", BUGUN, SEHIRLER)


def test_kucuk_harfli_kelime_sehir_sanilmaz():
    assert "destination" not in kural_tabanli_cikar("nice yıllara, roma rakamı", BUGUN, ["Nice", "Roma"])
