"""LLM yolunun testleri: gerçek servise gitmeden, sahte httpx ile (5. hafta)."""
import json
import sys
import types
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ai_cikarim  # noqa: E402
from ai_cikarim import cikar, dogrula, llm_cagir  # noqa: E402

BUGUN = date(2026, 11, 26)


class SahteCevap:
    def __init__(self, durum, govde):
        self.status_code = durum
        self._govde = govde
        self.text = json.dumps(govde) if not isinstance(govde, str) else govde

    def json(self):
        return self._govde


def llm_cevabi(icerik):
    return {"choices": [{"message": {"content": icerik}}]}


@pytest.fixture
def sahte_httpx(monkeypatch):
    """httpx.post çağrılarını kaydeder; cevaplar sırayla 'cevaplar' listesinden gelir."""
    modul = types.SimpleNamespace(cagrilar=[], cevaplar=[])

    class TimeoutException(Exception):
        pass

    def post(url, json=None, timeout=None, headers=None):
        modul.cagrilar.append({"url": url, "json": json, "headers": headers})
        cevap = modul.cevaplar.pop(0)
        if isinstance(cevap, Exception):
            raise cevap
        return cevap

    modul.post = post
    modul.TimeoutException = TimeoutException
    monkeypatch.setitem(sys.modules, "httpx", modul)
    monkeypatch.setenv("LLM_API_KEY", "test-anahtar")
    monkeypatch.setenv("LLM_BASE_URL", "https://ornek.test/v1/")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.delenv("LLM_REASONING_EFFORT", raising=False)
    return modul


def test_basarili_cagri_ve_istek_bicimi(sahte_httpx):
    sahte_httpx.cevaplar.append(SahteCevap(200, llm_cevabi('{"origin_city": "İzmir", "people_count": 2}')))
    veri, hata = llm_cagir(["İzmir'den 2 kişi"], BUGUN)
    assert hata is None and veri == {"origin_city": "İzmir", "people_count": 2}
    istek = sahte_httpx.cagrilar[0]
    assert istek["url"] == "https://ornek.test/v1/chat/completions"
    assert istek["json"]["model"] == "test-model"
    assert istek["json"]["response_format"] == {"type": "json_object"}
    assert istek["headers"]["Authorization"] == "Bearer test-anahtar"
    assert "2026-11-26" in istek["json"]["messages"][0]["content"]


def test_markdown_icindeki_json_okunur(sahte_httpx):
    sahte_httpx.cevaplar.append(SahteCevap(200, llm_cevabi('Tabii:\n```json\n{"people_count": 3}\n```')))
    veri, hata = llm_cagir(["3 kişi"], BUGUN)
    assert veri == {"people_count": 3} and hata is None


def test_400_gelirse_response_format_olmadan_tekrar_dener(sahte_httpx):
    sahte_httpx.cevaplar += [SahteCevap(400, {"error": "response_format desteklenmiyor"}),
                             SahteCevap(200, llm_cevabi('{"people_count": 1}'))]
    veri, _ = llm_cagir(["tek başıma"], BUGUN)
    assert veri == {"people_count": 1}
    assert "response_format" not in sahte_httpx.cagrilar[1]["json"]


def test_reasoning_effort_ayari(sahte_httpx, monkeypatch):
    monkeypatch.setenv("LLM_REASONING_EFFORT", "low")
    sahte_httpx.cevaplar.append(SahteCevap(200, llm_cevabi("{}")))
    llm_cagir(["x"], BUGUN)
    assert sahte_httpx.cagrilar[0]["json"]["reasoning_effort"] == "low"


@pytest.mark.parametrize("cevap,parca", [
    (SahteCevap(401, {"error": "invalid key"}), "401"),
    (SahteCevap(200, llm_cevabi("üzgünüm, yapamam")), "JSON"),
    (SahteCevap(200, llm_cevabi("{bozuk json}")), "geçersiz"),
])
def test_hatalar_mesajla_doner(sahte_httpx, cevap, parca):
    sahte_httpx.cevaplar.append(cevap)
    veri, hata = llm_cagir(["x"], BUGUN)
    assert veri is None and parca in hata


def test_zaman_asimi(sahte_httpx):
    sahte_httpx.cevaplar.append(sahte_httpx.TimeoutException())
    veri, hata = llm_cagir(["x"], BUGUN)
    assert veri is None and "cevap vermedi" in hata


def test_llm_hata_verirse_kurallarla_devam(sahte_httpx, caplog):
    sahte_httpx.cevaplar.append(SahteCevap(429, {"error": "rate limit"}))
    bilgi, kaynak = cikar(["İzmir'den 2 kişi"], BUGUN)
    assert kaynak == "kural" and bilgi["people_count"] == 2
    assert "429" in caplog.text


def test_llm_kurallarin_ustune_yazar_bosluklari_kurallar_doldurur(sahte_httpx):
    # LLM kişi sayısını 3 bulmuş, bütçeyi atlamış; bütçe kurallardan gelir
    sahte_httpx.cevaplar.append(SahteCevap(200, llm_cevabi(
        '{"origin_city": "İzmir", "people_count": 3, "budget_try": null}')))
    bilgi, kaynak = cikar(["İzmir'den 2 kişi, 40 bin TL"], BUGUN)
    assert kaynak == "llm"
    assert bilgi["people_count"] == 3 and bilgi["budget_try"] == 40000


def test_llmin_uydurdugu_kod_sehirden_duzeltilir():
    sozluk = {"izmir": ("İzmir", "ADB")}
    temiz, _, hatalar = dogrula({"origin_city": "İzmir", "origin_airport_code": "IZM"},
                                BUGUN, None, sozluk, {"ADB"})
    assert temiz["origin_airport_code"] == "ADB" and not hatalar


def test_anahtar_yoksa_llm_cagrilmaz(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    assert ai_cikarim.llm_ile_cikar(["x"], BUGUN) is None
