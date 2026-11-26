"""VoyageAI - 5. hafta (Kişi B): kullanıcının cümlesinden seyahat bilgisi çıkarma.

Bu dosya veritabanına bağlanmaz; tests/test_ai_cikarim.py ile test edilir.

İki yol vardır:
1. LLM (OpenAI uyumlu API: Gemini, Groq, OpenAI...). .env'de LLM_API_KEY,
   LLM_BASE_URL ve LLM_MODEL varsa kullanılır.
2. Kural tabanlı çıkarım: anahtar yoksa ya da LLM hata verirse devreye girer.
   Böylece demo internet/anahtar olmadan da çalışır.

LLM sadece bilgiyi çıkarır. Kontrol (tarih geçmiş mi, ağırlıklar 100 mü...)
ve kullanıcıya sorulacak soru her zaman bu dosyadaki kurallarla yapılır;
LLM'in uydurduğu bir değer kontrolsüz seyahate dönüşmez.
"""
from __future__ import annotations

import json
import os
import re
from datetime import date, timedelta

ALANLAR = [
    "origin_city", "origin_airport_code", "destination", "budget_try", "people_count",
    "start_date", "end_date",
    "nature_weight", "food_weight", "history_weight", "nightlife_weight",
]
AGIRLIKLAR = ["nature_weight", "food_weight", "history_weight", "nightlife_weight"]

# Kalkış şehri -> havalimanı (frontend/app/utils/havalimanlari.ts ile aynı + birkaç ek)
HAVALIMANLARI = {
    "İstanbul": "IST", "Ankara": "ESB", "İzmir": "ADB", "Antalya": "AYT",
    "Adana": "COV", "Trabzon": "TZX", "Gaziantep": "GZT", "Kayseri": "ASR",
    "Diyarbakır": "DIY", "Samsun": "SZF", "Bodrum": "BJV", "Dalaman": "DLM",
    "Bursa": "YEI", "Konya": "KYA", "Erzurum": "ERZ", "Van": "VAN",
    "Malatya": "MLX", "Hatay": "HTY", "Eskişehir": "AOE", "Denizli": "DNZ",
}
BILINEN_KODLAR = set(HAVALIMANLARI.values()) | {"SAW"}

AYLAR = {
    "ocak": 1, "şubat": 2, "mart": 3, "nisan": 4, "mayıs": 5, "haziran": 6,
    "temmuz": 7, "ağustos": 8, "eylül": 9, "ekim": 10, "kasım": 11, "aralık": 12,
}
SAYI_KELIMELERI = {
    "bir": 1, "iki": 2, "üç": 3, "dört": 4, "beş": 5, "altı": 6,
    "yedi": 7, "sekiz": 8, "dokuz": 9, "on": 10,
}
ILGI_KELIMELERI = {
    "nature_weight": ["doğa", "deniz", "plaj", "sahil", "kamp", "yürüyüş", "dağ", "göl",
                      "orman", "şelale", "park", "manzara", "yeşil"],
    "food_weight": ["yemek", "gastronomi", "lezzet", "restoran", "mutfak", "yeme içme",
                    "kahve", "tatlı", "şarap"],
    "history_weight": ["tarih", "müze", "antik", "kale", "saray", "kültür", "sanat",
                       "mimari", "katedral", "cami"],
    "nightlife_weight": ["gece hayatı", "gece", "eğlence", "parti", "bar", "kulüp",
                         "konser", "festival"],
}
OLUMSUZ = r"(istemiyorum|istemem|sevmiyorum|sevmem|olmasın|gerek yok|ilgilenmiyorum|hiç)"


# ---------------------------------------------------------------- yardımcılar

def kucult(metin: str) -> str:
    """Türkçe uyumlu küçük harf (İ->i, I->ı)."""
    return metin.replace("İ", "i").replace("I", "ı").lower()


def _sayi(deger: str) -> int | None:
    deger = deger.strip()
    if deger.isdigit():
        return int(deger)
    return SAYI_KELIMELERI.get(deger)


def _yil_sec(gun: int, ay: int, bugun: date, yil: int | None = None) -> date | None:
    """Yıl verilmediyse tarihin bugünden sonraki ilk denk geldiği yılı seç."""
    try:
        if yil:
            return date(yil, ay, gun)
        aday = date(bugun.year, ay, gun)
        return aday if aday >= bugun else date(bugun.year + 1, ay, gun)
    except ValueError:
        return None


def agirliklari_yuvarla(puanlar: dict[str, float]) -> dict[str, int]:
    """Puanları 5'in katı olacak ve toplamı tam 100 olacak şekilde dağıtır."""
    toplam = sum(puanlar.values())
    if toplam <= 0:
        return {k: 25 for k in AGIRLIKLAR}
    ham = {k: puanlar.get(k, 0) / toplam * 20 for k in AGIRLIKLAR}  # 20 adet 5'lik dilim
    tam = {k: int(v) for k, v in ham.items()}
    kalan = 20 - sum(tam.values())
    for k in sorted(AGIRLIKLAR, key=lambda k: ham[k] - tam[k], reverse=True)[:kalan]:
        tam[k] += 1
    return {k: v * 5 for k, v in tam.items()}


# ---------------------------------------------------------------- kural tabanlı

def varis_bul(metin: str, sehirler: list[str]) -> str | None:
    """Gidilecek şehri bulur: "Paris'e", "Roma'ya", "Viyana'da", "Lizbon gezisi".
    Sadece veritabanındaki şehir adları aranır; "İzmir'den" gibi kalkış ekleri sayılmaz."""
    k = kucult(metin)
    for sehir in sorted(sehirler, key=len, reverse=True):  # uzun ad önce (ör. "Ebu Simbel")
        s = re.escape(kucult(sehir))
        if re.search(rf"(?<!\w){s}['’]?(y?a|y?e|da|de|ta|te)(?!\w)", k) or re.search(
            rf"(?<!\w){s}['’]?\s+(gezisi|gezi|tatili|tatil|seyahati|turu|tur)\b", k
        ):
            return sehir
    # Eksiz yazıldıysa ("İzmir Roma 3 kişi"): şehir adı büyük harfle ayrı bir kelime olarak geçiyorsa
    for sehir in sorted(sehirler, key=len, reverse=True):
        if re.search(rf"(?<!\w){re.escape(sehir)}(?![\w'’])", metin) and not re.search(
            rf"(?<!\w){re.escape(kucult(sehir))}['’]?(den|dan|ten|tan|\s+çıkış|\s+kalkış)", k
        ):
            return sehir
    return None


def kural_tabanli_cikar(metin: str, bugun: date, sehirler: list[str] | None = None) -> dict:
    """Cümleden bulabildiği alanları döndürür. Bulamadığı alan sözlükte yer almaz."""
    k = kucult(metin)
    sonuc: dict = {}
    if sehirler:
        varis = varis_bul(metin, sehirler)
        if varis:
            sonuc["destination"] = varis

    # Kalkış şehri: "İzmir'den", "izmirden", "Ankara çıkışlı"
    for sehir, kod in HAVALIMANLARI.items():
        s = kucult(sehir)
        if re.search(rf"\b{s}['’]?\s*(den|dan|ten|tan)\b", k) or re.search(
            rf"\b{s}['’]?(den|dan|ten|tan)\b", k
        ) or re.search(rf"\b{s}\s+(çıkışlı|kalkışlı|çıkış|kalkış)", k):
            sonuc["origin_city"], sonuc["origin_airport_code"] = sehir, kod
            break
    kod_eslesme = re.search(r"\b([A-Z]{3})\b", metin)
    if kod_eslesme and kod_eslesme.group(1) in BILINEN_KODLAR:
        sonuc["origin_airport_code"] = kod_eslesme.group(1)

    # Bütçe: "40 bin TL", "40.000 TL", "40k", "bütçem 25 bin"
    butce = re.search(
        r"(\d{1,3}(?:[.\s]\d{3})+|\d+(?:,\d+)?)\s*(bin|k)?\s*(tl|lira|₺|türk lirası)\b", k
    ) or re.search(r"bütçe\w*\s*(?:de|da|ile|:)?\s*(\d{1,3}(?:[.\s]\d{3})+|\d+(?:,\d+)?)\s*(bin|k)?", k) \
      or re.search(r"(\d+(?:,\d+)?)\s*(bin|k)\b", k)
    if butce:
        sayi = float(re.sub(r"[.\s]", "", butce.group(1)).replace(",", "."))
        if butce.group(2) in ("bin", "k"):
            sayi *= 1000
        if sayi > 0:
            sonuc["budget_try"] = round(sayi, 2)

    # Kişi sayısı
    kisi = re.search(r"\b(\d+|" + "|".join(SAYI_KELIMELERI) + r")\s*(kişi|kişiyiz|kişilik)", k)
    if kisi and _sayi(kisi.group(1)):
        sonuc["people_count"] = _sayi(kisi.group(1))
    elif re.search(r"tek başıma|yalnız|kendim için|solo", k):
        sonuc["people_count"] = 1
    elif re.search(r"eşimle|sevgilimle|nişanlımla|kız arkadaşımla|erkek arkadaşımla|balayı", k):
        sonuc["people_count"] = 2

    # Tarihler
    ay_deseni = "|".join(AYLAR)
    t = (
        # 15.07.2027 - 20.07.2027
        re.search(r"(\d{1,2})[./](\d{1,2})[./](\d{4})\s*(?:-|–|ile|ve|'?(?:den|dan|ten|tan))\s*(\d{1,2})[./](\d{1,2})[./](\d{4})", k)
    )
    if t:
        bas = _yil_sec(int(t.group(1)), int(t.group(2)), bugun, int(t.group(3)))
        bit = _yil_sec(int(t.group(4)), int(t.group(5)), bugun, int(t.group(6)))
        if bas and bit:
            sonuc["start_date"], sonuc["end_date"] = bas.isoformat(), bit.isoformat()
    else:
        # 15 Temmuz - 20 Temmuz / 15 Temmuz'dan 20 Ağustos'a / 15-20 Temmuz
        iki_ay = re.search(
            rf"(\d{{1,2}})\s*({ay_deseni})\w*['’]?\s*(?:-|–|ile|ve|\w*den|\w*dan|\w*ten|\w*tan)?\s*(\d{{1,2}})\s*({ay_deseni})(?:\s*(\d{{4}}))?",
            k,
        )
        tek_ay = re.search(
            rf"(\d{{1,2}})\s*(?:-|–|ile|ve)\s*(\d{{1,2}})\s*({ay_deseni})(?:\s*(\d{{4}}))?", k
        )
        if iki_ay:
            yil = int(iki_ay.group(5)) if iki_ay.group(5) else None
            bas = _yil_sec(int(iki_ay.group(1)), AYLAR[iki_ay.group(2)], bugun, yil)
            bit = _yil_sec(int(iki_ay.group(3)), AYLAR[iki_ay.group(4)], bugun, yil)
            if bas and bit and bit <= bas and not yil:
                bit = _yil_sec(bit.day, bit.month, bugun, bas.year + 1)
            if bas and bit:
                sonuc["start_date"], sonuc["end_date"] = bas.isoformat(), bit.isoformat()
        elif tek_ay:
            yil = int(tek_ay.group(4)) if tek_ay.group(4) else None
            ay = AYLAR[tek_ay.group(3)]
            bas = _yil_sec(int(tek_ay.group(1)), ay, bugun, yil)
            bit = _yil_sec(int(tek_ay.group(2)), ay, bugun, bas.year if bas else yil)
            if bas and bit:
                sonuc["start_date"], sonuc["end_date"] = bas.isoformat(), bit.isoformat()
        else:
            # "15 Temmuz'da 5 gün" / "5 gece"
            tek = re.search(rf"(\d{{1,2}})\s*({ay_deseni})(?:\s*(\d{{4}}))?", k)
            if tek:
                bas = _yil_sec(int(tek.group(1)), AYLAR[tek.group(2)], bugun,
                               int(tek.group(3)) if tek.group(3) else None)
                if bas:
                    sonuc["start_date"] = bas.isoformat()
                    sure = re.search(r"(\d+|" + "|".join(SAYI_KELIMELERI) + r")\s*(gün|gece)", k)
                    if sure and _sayi(sure.group(1)):
                        n = _sayi(sure.group(1))
                        gun_say = n if sure.group(2) == "gece" else max(1, n - 1)
                        sonuc["end_date"] = (bas + timedelta(days=gun_say)).isoformat()

    # İlgi alanları
    puan: dict[str, float] = {}
    bahsedildi = False
    for alan, kelimeler in ILGI_KELIMELERI.items():
        for kelime in kelimeler:
            for m in re.finditer(rf"\b{kelime}", k):
                bahsedildi = True
                sonra = k[m.end(): m.end() + 30]
                if re.search(OLUMSUZ, sonra):
                    puan[alan] = -1  # açıkça istemiyor
                elif puan.get(alan, 0) >= 0:
                    vurgu = re.search(r"ağırlıklı|özellikle|çok|en çok|bayılırım|seviyorum", sonra)
                    puan[alan] = puan.get(alan, 0) + (2 if vurgu else 1)
    if bahsedildi:
        olumlu = {a: v for a, v in puan.items() if v > 0}
        if olumlu:
            # Bahsedilen alanlar 3 kat, bahsedilmeyenler 1 kat; istemedikleri 0.
            tablo = {}
            for a in AGIRLIKLAR:
                if puan.get(a, 0) < 0:
                    tablo[a] = 0
                elif a in olumlu:
                    tablo[a] = 3 * olumlu[a]
                else:
                    tablo[a] = 1
            sonuc.update(agirliklari_yuvarla(tablo))

    # "İzmir'de yaşıyorum, İzmir'den..." gibi durumlarda kalkış şehri varış sayılmasın
    if sonuc.get("destination") and sonuc.get("destination") == sonuc.get("origin_city"):
        del sonuc["destination"]
    return sonuc


# ---------------------------------------------------------------- LLM

SISTEM_ISTEMI = """Sen VoyageAI seyahat asistanının bilgi çıkarma modülüsün.
Kullanıcının mesajlarından seyahat bilgilerini çıkar ve SADECE bir JSON nesnesi döndür.
Bugünün tarihi: {bugun}.

Alanlar (bilmediğin alanı null bırak, ASLA tahmin etme ya da uydurma):
- origin_city: kalkış şehri (Türkçe ad, örn. "İzmir")
- origin_airport_code: kalkış havalimanı IATA kodu (biliyorsan, örn. "ADB")
- destination: gitmek istediği şehir, Türkçe adıyla (örn. "Roma", "Viyana"). Söylemediyse null.
- budget_try: toplam bütçe, Türk lirası, sayı (örn. "40 bin" -> 40000). Başka para birimi ise null.
- people_count: kişi sayısı, tam sayı
- start_date, end_date: "YYYY-AA-GG". Yıl söylenmediyse bugünden sonraki ilk tarih.
- nature_weight, food_weight, history_weight, nightlife_weight: kullanıcının doğa, yemek,
  tarih/kültür ve gece hayatına verdiği önem; toplamı 100, 5'in katları. Kullanıcı ilgi
  alanından hiç bahsetmediyse dördü de null.
"""


def llm_ayarli() -> bool:
    return bool(os.getenv("LLM_API_KEY") and os.getenv("LLM_BASE_URL") and os.getenv("LLM_MODEL"))


def llm_ile_cikar(kullanici_mesajlari: list[str], bugun: date, zaman_asimi: float = 20) -> dict | None:
    """OpenAI uyumlu /chat/completions ile çıkarım. Hata olursa None döner."""
    if not llm_ayarli():
        return None
    import httpx

    url = os.getenv("LLM_BASE_URL", "").rstrip("/") + "/chat/completions"
    govde = {
        "model": os.getenv("LLM_MODEL"),
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SISTEM_ISTEMI.format(bugun=bugun.isoformat())},
            {"role": "user", "content": "\n".join(f"- {m}" for m in kullanici_mesajlari)},
        ],
    }
    try:
        cevap = httpx.post(
            url, json=govde, timeout=zaman_asimi,
            headers={"Authorization": f"Bearer {os.getenv('LLM_API_KEY')}"},
        )
        cevap.raise_for_status()
        icerik = cevap.json()["choices"][0]["message"]["content"]
        icerik = re.sub(r"^```(?:json)?|```$", "", icerik.strip()).strip()
        veri = json.loads(icerik)
    except Exception:
        return None
    if not isinstance(veri, dict):
        return None
    return {a: veri[a] for a in ALANLAR if veri.get(a) not in (None, "")}


def cikar(kullanici_mesajlari: list[str], bugun: date,
          sehirler: list[str] | None = None) -> tuple[dict, str]:
    """Bütün kullanıcı mesajlarından bilgi çıkarır. (bilgi, kaynak) döner."""
    kural: dict = {}
    for mesaj in kullanici_mesajlari:  # sonraki mesaj öncekini günceller
        kural = birlestir(kural, kural_tabanli_cikar(mesaj, bugun, sehirler))
    llm = llm_ile_cikar(kullanici_mesajlari, bugun)
    if llm is None:
        return kural, "kural"
    # LLM'in boş bıraktığını kurallarla tamamla
    return birlestir(kural, llm), "llm"


# ---------------------------------------------------------------- birleştirme ve kontrol

def birlestir(eski: dict, yeni: dict) -> dict:
    """Yeni gelen dolu alanlar eskisinin üstüne yazılır. Ağırlıklar dörtlü grup olarak değişir."""
    sonuc = dict(eski)
    for alan, deger in yeni.items():
        if alan in AGIRLIKLAR or deger in (None, ""):
            continue
        sonuc[alan] = deger
    if any(yeni.get(a) is not None for a in AGIRLIKLAR):
        for a in AGIRLIKLAR:
            sonuc[a] = yeni.get(a) or 0
    return sonuc


def _tarih(deger) -> date | None:
    if isinstance(deger, date):
        return deger
    try:
        return date.fromisoformat(str(deger)[:10])
    except (TypeError, ValueError):
        return None


def dogrula(bilgi: dict, bugun: date,
            sehirler: list[str] | None = None) -> tuple[dict, list[str], list[str]]:
    """(temiz_bilgi, eksik_alanlar, hata_mesajlari) döndürür.

    Gidilecek şehir isteğe bağlıdır. Verildiyse ve şehir listesinde yoksa
    seyahati engellemez; temiz["varis_notu"] ile kullanıcıya söylenir.
    """
    temiz = dict(bilgi)
    temiz.pop("varis_notu", None)
    eksik: list[str] = []
    hatalar: list[str] = []

    varis = str(temiz.get("destination") or "").strip()
    if not varis:
        temiz["destination"] = None
    elif sehirler is not None:
        eslesen = next((s for s in sehirler if kucult(s) == kucult(varis)), None)
        temiz["destination"] = eslesen
        if eslesen is None:
            temiz["varis_notu"] = (
                f"{varis} şu an şehir listemizde yok; seyahat oluşunca sana önerilen "
                "şehirlerden birini seçebilirsin."
            )

    sehir = str(temiz.get("origin_city") or "").strip()
    if sehir:
        eslesen = next((s for s in HAVALIMANLARI if kucult(s) == kucult(sehir)), None)
        if eslesen:
            temiz["origin_city"] = eslesen
            if not temiz.get("origin_airport_code"):
                temiz["origin_airport_code"] = HAVALIMANLARI[eslesen]
    else:
        eksik.append("origin_city")
    kod = str(temiz.get("origin_airport_code") or "").strip().upper()
    if kod:
        temiz["origin_airport_code"] = kod
    elif sehir:
        eksik.append("origin_airport_code")

    try:
        butce = float(temiz.get("budget_try")) if temiz.get("budget_try") is not None else None
    except (TypeError, ValueError):
        butce = None
    if butce is None:
        eksik.append("budget_try")
    elif butce <= 0:
        hatalar.append("Bütçe sıfırdan büyük olmalı.")
    else:
        temiz["budget_try"] = round(butce, 2)

    try:
        kisi = int(temiz.get("people_count")) if temiz.get("people_count") is not None else None
    except (TypeError, ValueError):
        kisi = None
    if kisi is None:
        eksik.append("people_count")
    elif not 1 <= kisi <= 20:
        hatalar.append("Kişi sayısı 1 ile 20 arasında olmalı.")
    else:
        temiz["people_count"] = kisi

    bas, bit = _tarih(temiz.get("start_date")), _tarih(temiz.get("end_date"))
    if bas is None:
        eksik.append("start_date")
    if bit is None:
        eksik.append("end_date")
    if bas and bas < bugun:
        hatalar.append("Başlangıç tarihi geçmişte kalıyor.")
    if bas and bit and bit <= bas:
        hatalar.append("Dönüş tarihi gidiş tarihinden sonra olmalı.")
    if bas:
        temiz["start_date"] = bas.isoformat()
    if bit:
        temiz["end_date"] = bit.isoformat()

    agirlik = []
    for a in AGIRLIKLAR:
        try:
            agirlik.append(max(0, int(temiz.get(a)))) if temiz.get(a) is not None else None
        except (TypeError, ValueError):
            pass
    if len(agirlik) < 4 or sum(agirlik) == 0:
        eksik.append("interests")
    else:
        temiz.update(agirliklari_yuvarla(dict(zip(AGIRLIKLAR, agirlik))))

    return temiz, eksik, hatalar


SORULAR = {
    "origin_city": "Hangi şehirden yola çıkacaksın?",
    "origin_airport_code": "Hangi havalimanından uçacaksın? (örn. IST, SAW, ADB)",
    "start_date": "Hangi tarihler arasında gitmek istiyorsun? (örn. 15-20 Temmuz)",
    "end_date": "Ne zaman döneceksin ya da kaç gün kalacaksın?",
    "budget_try": "Toplam bütçen ne kadar? (örn. 40 bin TL)",
    "people_count": "Kaç kişi gideceksiniz?",
    "interests": "Seyahatte en çok neyden hoşlanırsın: doğa, yemek, tarih/kültür, gece hayatı?",
}


def yanit_uret(eksik: list[str], hatalar: list[str]) -> str:
    """Kullanıcıya gösterilecek asistan cevabı (kurallı, LLM'e bırakılmaz)."""
    if hatalar:
        return " ".join(hatalar) + " Düzeltebilir misin?"
    if eksik:
        # Tarihler tek soruda sorulur
        sorular = []
        for alan in eksik:
            if alan == "end_date" and "start_date" in eksik:
                continue
            sorular.append(SORULAR[alan])
        if len(sorular) == 1:
            return sorular[0]
        return "Birkaç bilgi daha lazım: " + " ".join(sorular[:2])
    return "Harika, gerekli her şey tamam! Anladığım bilgileri kartta gösterdim; kontrol et, gerekirse düzelt ve onayla."


def baslik_uret(bilgi: dict) -> str:
    bas, bit = _tarih(bilgi.get("start_date")), _tarih(bilgi.get("end_date"))
    tarih = f" ({bas:%d.%m}–{bit:%d.%m.%Y})" if bas and bit else ""
    if bilgi.get("destination"):
        return f"{bilgi.get('origin_city', 'Yeni')} → {bilgi['destination']} seyahati{tarih}"[:150]
    return f"{bilgi.get('origin_city', 'Yeni')} çıkışlı seyahat{tarih}"[:150]
