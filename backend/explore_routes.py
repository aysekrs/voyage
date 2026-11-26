"""Keşfet sayfası için şehir listesi (kategori sayılarıyla birlikte).

GET /explore/cities            -> her şehir için kaç gezilecek yer olduğu ve
                                  bunların tarih/doğa/yemek/gece hayatı dağılımı.
GET /explore/cities/{id}/photo -> şehrin Vikipedi'deki ana fotoğrafı
                                  (Wikimedia Commons, serbest lisanslı).
Sadece okur; B'nin sehirler/yerler tablolarını değiştirmez.
"""
import httpx
from fastapi import APIRouter, HTTPException
from sqlalchemy import case, func, select

from city_models import Sehir, Yer
from database import SessionLocal

router = APIRouter(tags=["Explore"])


def _sayac(kategori: str):
    return func.coalesce(func.sum(case((Yer.kategori == kategori, 1), else_=0)), 0)


@router.get("/explore/cities")
def explore_cities():
    db = SessionLocal()
    try:
        satirlar = db.execute(
            select(
                Sehir.sehir_id,
                Sehir.ad,
                Sehir.ulke,
                func.count(Yer.yer_id).label("toplam"),
                _sayac("tarih").label("tarih"),
                _sayac("doğa").label("doga"),
                _sayac("yemek").label("yemek"),
                _sayac("gece_hayati").label("gece"),
            )
            .outerjoin(Yer, Yer.sehir_id == Sehir.sehir_id)
            .group_by(Sehir.sehir_id)
            .order_by(func.count(Yer.yer_id).desc(), Sehir.ad)
        ).all()

        return [
            {
                "id": s.sehir_id,
                "name": s.ad,
                "country": s.ulke,
                "place_count": s.toplam,
                "categories": {
                    "history": s.tarih,
                    "nature": s.doga,
                    "food": s.yemek,
                    "nightlife": s.gece,
                },
            }
            for s in satirlar
        ]
    finally:
        db.close()


# ---------------------------------------------------------------
# Şehir fotoğrafı (Vikipedi). Sonuç bellekte saklanır; her şehir
# için Vikipedi'ye sunucu açık kaldığı sürece bir kez gidilir.
# ---------------------------------------------------------------

VIKIPEDI_API = "https://tr.wikipedia.org/w/api.php"
VIKIPEDI_BASLIK = {"User-Agent": "VoyageAI/1.0 (bitirme projesi; egitim amacli)"}
FOTO_GENISLIK = 900
_foto_onbellek: dict[int, dict] = {}


def _vikipedi_fotografi(baslik: str) -> dict | None:
    cevap = httpx.get(
        VIKIPEDI_API,
        params={
            "action": "query",
            "format": "json",
            "formatversion": 2,
            "redirects": 1,
            "titles": baslik,
            "prop": "pageimages|pageprops|info",
            "piprop": "thumbnail",
            "pithumbsize": FOTO_GENISLIK,
            "inprop": "url",
        },
        headers=VIKIPEDI_BASLIK,
        timeout=6,
    )
    cevap.raise_for_status()
    sayfalar = cevap.json().get("query", {}).get("pages", [])
    if not sayfalar:
        return None
    sayfa = sayfalar[0]
    if sayfa.get("missing") or "disambiguation" in sayfa.get("pageprops", {}):
        return None
    kucuk = sayfa.get("thumbnail")
    if not kucuk:
        return None
    return {"url": kucuk["source"], "page_url": sayfa.get("fullurl")}


@router.get("/explore/cities/{destination_id}/photo")
def city_photo(destination_id: int):
    if destination_id in _foto_onbellek:
        return _foto_onbellek[destination_id]

    db = SessionLocal()
    try:
        sehir = db.get(Sehir, destination_id)
    finally:
        db.close()
    if sehir is None:
        raise HTTPException(404, "Şehir bulunamadı.")

    sonuc = {"url": None, "page_url": None, "source": "Vikipedi / Wikimedia Commons"}
    try:
        # Önce şehir adı, olmazsa "Şehir, Ülke" biçimi
        for baslik in (sehir.ad, f"{sehir.ad}, {sehir.ulke}"):
            bulunan = _vikipedi_fotografi(baslik)
            if bulunan:
                sonuc.update(bulunan)
                break
    except (httpx.HTTPError, ValueError):
        return sonuc  # geçici hata: önbelleğe yazma, sonra tekrar denensin

    _foto_onbellek[destination_id] = sonuc
    return sonuc
