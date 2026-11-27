"""AI asistanın yapay zekâ (LLM) bağlantısını dener.

Kullanım (backend klasöründe):
    python llm_dene.py              -> ayarları kontrol eder, örnek cümlelerle dener
    python llm_dene.py --modeller   -> anahtarınla kullanılabilen model adlarını listeler

.env dosyasında şunlar olmalı (bkz. .env.example):
    LLM_API_KEY=...
    LLM_BASE_URL=...
    LLM_MODEL=...
"""
import os
import sys
import time
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from ai_cikarim import ALANLAR, kural_tabanli_cikar, llm_ayarli, llm_cagir  # noqa: E402

ORNEKLER = [
    "İzmir'den Roma'ya 2 kişi 15-20 Temmuz arası 40 bin TL bütçeyle, tarih ve yemek ağırlıklı",
    "Eşimle Münih'ten çıkıp 10 Mayıs'ta 4 gece bir yere gitmek istiyoruz, doğa olsun, gece hayatı istemiyorum",
    "Ankara çıkışlı, 3 kişiyiz, bütçemiz yüz yirmi bin lira, müzeleri ve gece hayatını seviyoruz",
]


def gizle(anahtar: str) -> str:
    return anahtar[:4] + "…" + anahtar[-4:] if len(anahtar) > 10 else "(çok kısa)"


def ayarlari_yaz() -> bool:
    print("Ayarlar (.env):")
    for ad in ("LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY", "LLM_REASONING_EFFORT"):
        deger = os.getenv(ad, "")
        if ad == "LLM_API_KEY" and deger:
            deger = gizle(deger)
        print(f"  {ad:22} {deger or '(boş)'}")
    if not llm_ayarli():
        print("\nEKSİK: LLM_API_KEY, LLM_BASE_URL ve LLM_MODEL üçü de dolu olmalı.")
        return False
    return True


def modelleri_listele() -> None:
    import httpx

    url = os.getenv("LLM_BASE_URL", "").rstrip("/") + "/models"
    cevap = httpx.get(url, timeout=20, headers={"Authorization": f"Bearer {os.getenv('LLM_API_KEY')}"})
    if cevap.status_code >= 400:
        print(f"HATA {cevap.status_code}: {cevap.text[:300]}")
        return
    adlar = sorted(m.get("id", "") for m in cevap.json().get("data", []))
    print(f"{len(adlar)} model:")
    for ad in adlar:
        print("  ", ad.removeprefix("models/"))


def main() -> None:
    if not ayarlari_yaz():
        raise SystemExit(1)
    if "--modeller" in sys.argv:
        modelleri_listele()
        return

    bugun = date.today()
    basarili = 0
    for cumle in ORNEKLER:
        print("\n" + "=" * 70)
        print("Cümle:", cumle)
        bas = time.perf_counter()
        veri, hata = llm_cagir([cumle], bugun)
        sure = time.perf_counter() - bas
        if hata:
            print(f"  HATA ({sure:.1f} sn): {hata}")
            continue
        basarili += 1
        kural = kural_tabanli_cikar(cumle, bugun)
        print(f"  Yapay zekâ cevabı ({sure:.1f} sn):")
        for alan in ALANLAR:
            fark = "" if kural.get(alan) in (None, veri.get(alan)) else f"   (kurallar: {kural[alan]})"
            print(f"    {alan:20} {veri.get(alan)}{fark}")

    print("\n" + "=" * 70)
    if basarili == len(ORNEKLER):
        print("BAŞARILI: Yapay zekâ bağlantısı çalışıyor. Backend'i yeniden başlatınca asistan kullanır.")
    elif basarili:
        print(f"KISMEN: {basarili}/{len(ORNEKLER)} cümle çalıştı. Hataları yukarıda gör.")
    else:
        print("ÇALIŞMADI. İpuçları:")
        print("  * HTTP 401/403 -> anahtar yanlış ya da kopyalarken eksik kalmış")
        print("  * HTTP 404     -> model adı yanlış:  python llm_dene.py --modeller")
        print("  * HTTP 429     -> ücretsiz kullanım sınırı doldu, biraz bekleyip tekrar dene")
        print("  * HTTP 503 / cevap vermedi -> model şu an yoğun. LLM_MODEL'e virgülle yedek model ekle:")
        print("                   LLM_MODEL=birinci-model,yedek-model   (liste: python llm_dene.py --modeller)")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
