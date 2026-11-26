"""Havalimanı arama API'si (kalkış şehri seçimi).

GET /airports?q=mun     -> en uygun 8 havalimanı (Münih, Munich, MUC ...)
GET /airports?q=        -> boşsa Türkiye'nin büyük havalimanları
GET /airports/{iata}    -> tek havalimanı

Veri: airports tablosu (alembic d4a9e2b6c813, veri/havalimanlari.csv).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from havalimani_arama import gorunen_ad, normalize

router = APIRouter(prefix="/airports", tags=["Havalimanları"])

ALANLAR = "iata, name, city, city_tr, country_code, country, country_tr, lat, lon, type"
VARSAYILAN = ["IST", "SAW", "ESB", "ADB", "AYT", "DLM", "BJV", "TZX"]


def _conn():
    import main  # döngüsel içe aktarmayı önlemek için geç yükleme
    return main.conn()


def _cikti(satir: dict) -> dict:
    sonuc = {k: satir[k] for k in ALANLAR.split(", ")}
    sonuc["label"] = gorunen_ad(satir)
    sonuc["city_display"] = satir["city_tr"] or satir["city"]
    sonuc["country_display"] = satir["country_tr"] or satir["country"]
    return sonuc


def havalimani_getir(db, iata: str | None) -> dict | None:
    """Kod tabloda varsa satırı döndürür (seyahat kontrolleri de kullanır)."""
    if not iata or len(iata.strip()) != 3:
        return None
    return db.execute(
        f"SELECT {ALANLAR} FROM airports WHERE iata = %s", (iata.strip().upper(),)
    ).fetchone()


@router.get("")
def havalimani_ara(q: str = Query("", max_length=60), limit: int = Query(8, ge=1, le=20)):
    aranan = normalize(q)
    with _conn() as db:
        if len(aranan) < 2:
            satirlar = db.execute(
                f"SELECT {ALANLAR} FROM airports WHERE iata = ANY(%s) "
                "ORDER BY array_position(%s::text[], iata::text)",
                (VARSAYILAN, VARSAYILAN),
            ).fetchall()
            return [_cikti(s) for s in satirlar]

        satirlar = db.execute(
            f"""
            SELECT {ALANLAR},
                CASE
                    WHEN iata = %(kod)s THEN 0
                    WHEN sehir_arama LIKE %(bas)s THEN 1
                    WHEN sehir_arama LIKE %(kelime_basi)s THEN 2
                    WHEN arama LIKE %(kelime_basi)s THEN 3
                    ELSE 4
                END AS sira
            FROM airports
            WHERE arama LIKE %(icinde)s OR iata = %(kod)s
            ORDER BY sira,
                     (city_tr IS NOT NULL) DESC,
                     CASE type WHEN 'large' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
                     (country_code = 'TR') DESC,
                     iata
            LIMIT %(limit)s
            """,
            {
                "kod": q.strip().upper(),
                "bas": f" {aranan}%",
                "kelime_basi": f"% {aranan}%",
                "icinde": f"%{aranan}%",
                "limit": limit,
            },
        ).fetchall()
    return [_cikti(s) for s in satirlar]


@router.get("/{iata}")
def havalimani_detay(iata: str):
    with _conn() as db:
        satir = havalimani_getir(db, iata)
    if not satir:
        raise HTTPException(404, "Havalimanı bulunamadı.")
    return _cikti(satir)
