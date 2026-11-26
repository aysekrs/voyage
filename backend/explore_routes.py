"""Keşfet sayfası için şehir listesi (kategori sayılarıyla birlikte).

GET /explore/cities -> her şehir için kaç gezilecek yer olduğu ve
                       bunların tarih/doğa/yemek/gece hayatı dağılımı.
(Şehir fotoğrafları tarayıcıdan doğrudan Vikipedi'den alınır.)
Sadece okur; B'nin sehirler/yerler tablolarını değiştirmez.
"""
from fastapi import APIRouter
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

