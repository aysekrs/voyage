from fastapi import APIRouter
router = APIRouter()

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from oneri_motoru import oneri_hesapla
from database import SessionLocal
from city_models import Sehir, Yer
from rota_servisi import router as rota_router


# Frontend uygulamas─▒n─▒n eri┼şim izni




# Veritaban─▒ ba─şlant─▒s─▒
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/")
def home():
    return {
        "message": "VoyageAI API basariyla calisiyor!"
    }


# B├╝t├╝n ┼şehirleri listele
@router.get("/destinations")
def get_destinations(db: Session = Depends(get_db)):
    sehirler = db.query(Sehir).order_by(
        Sehir.ulke,
        Sehir.ad
    ).all()

    return [
        {
            "id": s.sehir_id,
            "name": s.ad,
            "country": s.ulke,
            "airport_code": s.havalimani_kodu,
            "currency": s.para_birimi,
            "nature_score": s.doga_puani,
            "food_score": s.yemek_puani,
            "history_score": s.tarih_puani,
            "nightlife_score": s.gece_hayati_puani
        }
        for s in sehirler
    ]


def en_yakin_havalimani(db: Session, sehir) -> dict:
    """Sehrin havalimani kodu; yoksa (Versay, Brugge, Zermatt...) en yakin
    havalimanli sehrinkini verir. Sehir merkezi = gezilecek yerlerin ortalamasi."""
    if sehir.havalimani_kodu:
        return {"code": sehir.havalimani_kodu, "city": sehir.ad, "distance_km": 0}

    merkezler = db.execute(text("""
        SELECT s.sehir_id, s.ad, s.havalimani_kodu,
               AVG(y.enlem) AS lat, AVG(y.boylam) AS lon
        FROM sehirler s JOIN yerler y ON y.sehir_id = s.sehir_id
        WHERE y.enlem IS NOT NULL AND y.boylam IS NOT NULL
        GROUP BY s.sehir_id, s.ad, s.havalimani_kodu
    """)).mappings().all()
    bu = next((m for m in merkezler if m["sehir_id"] == sehir.sehir_id), None)
    adaylar = [m for m in merkezler if m["havalimani_kodu"]]
    if bu is None or not adaylar:
        return {"code": None, "city": None, "distance_km": None}

    from rota_algoritmasi import haversine
    en_yakin = min(adaylar, key=lambda m: haversine(bu["lat"], bu["lon"], m["lat"], m["lon"]))
    km = haversine(bu["lat"], bu["lon"], en_yakin["lat"], en_yakin["lon"])
    return {"code": en_yakin["havalimani_kodu"], "city": en_yakin["ad"], "distance_km": round(km)}


# Belirli bir ┼şehrin detaylar─▒n─▒ getir
@router.get("/destinations/{destination_id}")
def get_destination(
    destination_id: int,
    db: Session = Depends(get_db)
):
    sehir = db.query(Sehir).filter(
        Sehir.sehir_id == destination_id
    ).first()

    if sehir is None:
        raise HTTPException(
            status_code=404,
            detail="Sehir bulunamadi"
        )

    havalimani = en_yakin_havalimani(db, sehir)

    return {
        "id": sehir.sehir_id,
        "name": sehir.ad,
        "country": sehir.ulke,
        "airport_code": havalimani["code"],
        "airport_city": havalimani["city"],
        "airport_distance_km": havalimani["distance_km"],
        "currency": sehir.para_birimi,
        "nature_score": sehir.doga_puani,
        "food_score": sehir.yemek_puani,
        "history_score": sehir.tarih_puani,
        "nightlife_score": sehir.gece_hayati_puani
    }


# ┼Şehrin gezilecek yerlerini getir
@router.get("/destinations/{destination_id}/places")
def get_places(
    destination_id: int,
    db: Session = Depends(get_db)
):
    sehir = db.query(Sehir).filter(
        Sehir.sehir_id == destination_id
    ).first()

    if sehir is None:
        raise HTTPException(
            status_code=404,
            detail="Sehir bulunamadi"
        )

    yerler = db.query(Yer).filter(
        Yer.sehir_id == destination_id
    ).order_by(Yer.ad).all()

    # Hafta 2 kaynak denetimi yaln─▒zca be┼ş pilot ┼şehir i├ğin haz─▒r.
    # Di─şer ┼şehirlerin mevcut API ├ğ─▒kt─▒s─▒ de─şi┼şmeden kal─▒r.
    pilot_sehirler = {1, 8, 24, 39, 82}
    kontrol = {}
    # hafta2_api_yerler sadece B'nin veritabanında var; başka bir
    # veritabanında yoksa kaynak bilgisi "kaynak_bekliyor" olarak döner.
    kontrol_tablosu_var = db.execute(
        text("SELECT to_regclass('hafta2_api_yerler') IS NOT NULL")
    ).scalar()
    if destination_id in pilot_sehirler and kontrol_tablosu_var:
        satirlar = db.execute(
            text("""
                SELECT yer_id, kaynak_durumu, kaynak_url,
                       dogrulama_notu, kontrol_tarihi,
                       koordinat_mevcut, fiyat_mevcut,
                       ziyaret_kaynagi_bulundu, ziyaret_kosulu_uyarisi,
                       fiyat_para_birimi, fiyat_turu
                FROM hafta2_api_yerler
                WHERE sehir_id = :sehir_id
            """),
            {"sehir_id": destination_id}
        ).mappings().all()
        kontrol = {satir["yer_id"]: satir for satir in satirlar}

    sonuc = []
    for y in yerler:
        yer = {
            "id": y.yer_id,
            "name": y.ad,
            "category": y.kategori,
            "latitude": y.enlem,
            "longitude": y.boylam,
            "visit_duration": y.ziyaret_suresi,
            "average_price": y.ortalama_ucret,
            "price_currency": y.fiyat_para_birimi or sehir.para_birimi
        }
        if destination_id in pilot_sehirler:
            bilgi = kontrol.get(y.yer_id)
            yer.update({
                "source_status": bilgi["kaynak_durumu"] if bilgi else "kaynak_bekliyor",
                "source_url": bilgi["kaynak_url"] if bilgi else None,
                "verification_note": bilgi["dogrulama_notu"] if bilgi else None,
                "checked_at": (bilgi["kontrol_tarihi"].isoformat()
                               if bilgi and bilgi["kontrol_tarihi"] else None),
                "has_coordinates": bool(bilgi["koordinat_mevcut"]) if bilgi else False,
                "has_price": bool(bilgi["fiyat_mevcut"]) if bilgi else False,
                "visit_source_found": bool(bilgi["ziyaret_kaynagi_bulundu"]) if bilgi else False,
                "visit_warning": bool(bilgi["ziyaret_kosulu_uyarisi"]) if bilgi else False,
                "currency": bilgi["fiyat_para_birimi"] if bilgi else None,
                "price_type": bilgi["fiyat_turu"] if bilgi else None,
                # Konumun DB'de olmas─▒ giri┼ş noktas─▒n─▒n do─şruland─▒─ş─▒ anlam─▒na gelmez.
                "entrance_coordinates_verified": False
            })
        sonuc.append(yer)
    return sonuc


@router.get("/recommendations")
def get_recommendations(
    doga: int = 30,
    yemek: int = 20,
    tarih: int = 40,
    gece: int = 10
):
    tercihler = {
        "doga": doga,
        "yemek": yemek,
        "tarih": tarih,
        "gece": gece
    }

    if any(p < 0 or p > 100 for p in tercihler.values()):
        raise HTTPException(
            status_code=400,
            detail="Tercihler 0 ile 100 arasinda olmali."
        )

    if sum(tercihler.values()) == 0:
        raise HTTPException(
            status_code=400,
            detail="En az bir tercih 0'dan buyuk olmali."
        )

    try:
        oneriler = oneri_hesapla(tercihler)
        return {
            "tercihler": tercihler,
            "oneriler": oneriler[:5],
            "aciklama": (
                "Sonuclar kayitli gezilecek yerlerin "
                "kategori dagilimina dayali prototip onerilerdir."
            )
        }

    except (OSError, ValueError) as hata:
        raise HTTPException(
            status_code=500,
            detail=f"Oneri hesaplama hatasi: {hata}"
        )

@router.get("/map/places")
def get_map_places(city_id: int):
    db = SessionLocal()

    try:
        # ├ûnce do─şrulanm─▒┼ş koordinatlar─▒ getir.
        verified = db.execute(
            text("""
                SELECT
                    y.yer_id AS id,
                    y.ad AS name,
                    y.enlem AS latitude,
                    y.boylam AS longitude,
                    'verified' AS status
                FROM yerler y
                WHERE y.sehir_id = :city_id
                  AND y.enlem IS NOT NULL
                  AND y.boylam IS NOT NULL
            """),
            {"city_id": city_id}
        ).mappings().all()

        # Aday koordinatlar─▒ ayr─▒ getir.
        # Aday koordinat tabloları sadece B'nin veritabanında var;
        # yoksa harita sadece doğrulanmış konumları gösterir.
        aday_tablolari_var = db.execute(text("""
            SELECT to_regclass('koordinat_adaylari') IS NOT NULL
               AND to_regclass('hafta2_koordinat_uyarilari') IS NOT NULL
        """)).scalar()
        candidates = []
        if aday_tablolari_var:
            candidates = db.execute(
                text("""
                    SELECT
                        y.yer_id AS id,
                        y.ad AS name,
                        k.enlem AS latitude,
                        k.boylam AS longitude,
                        'candidate' AS status
                    FROM koordinat_adaylari k
                    JOIN yerler y ON y.yer_id = k.yer_id
                    WHERE y.sehir_id = :city_id
                      AND k.enlem IS NOT NULL
                      AND k.boylam IS NOT NULL
                      AND (y.enlem IS NULL OR y.boylam IS NULL)
                      AND NOT EXISTS (
                          SELECT 1
                          FROM hafta2_koordinat_uyarilari u
                          WHERE u.yer_id = y.yer_id
                            AND u.denetim_durumu = 'SUPHELI_KOORDINAT'
                      )
                """),
                {"city_id": city_id}
            ).mappings().all()

        return {
            "verified": [dict(row) for row in verified],
            "candidates": [dict(row) for row in candidates]
        }

    finally:
        db.close()
       


router.include_router(rota_router)
