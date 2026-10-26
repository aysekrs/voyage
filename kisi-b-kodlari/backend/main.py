
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from oneri_motoru import oneri_hesapla
from database import SessionLocal
from city_models import Sehir, Yer
from rota_servisi import router as rota_router

app = FastAPI(
    title="VoyageAI API",
    description="Yapay Zeka Destekli Seyahat Planlama Sistemi",
    version="1.0.0"
)
app.include_router(rota_router)

# Frontend uygulamasının erişim izni

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3005",
        "http://127.0.0.1:3005"
    ],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)



# Veritabanı bağlantısı
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def home():
    return {
        "message": "VoyageAI API basariyla calisiyor!"
    }


# Bütün şehirleri listele
@app.get("/destinations")
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


# Belirli bir şehrin detaylarını getir
@app.get("/destinations/{destination_id}")
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

    return {
        "id": sehir.sehir_id,
        "name": sehir.ad,
        "country": sehir.ulke,
        "currency": sehir.para_birimi,
        "nature_score": sehir.doga_puani,
        "food_score": sehir.yemek_puani,
        "history_score": sehir.tarih_puani,
        "nightlife_score": sehir.gece_hayati_puani
    }


# Şehrin gezilecek yerlerini getir
@app.get("/destinations/{destination_id}/places")
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

    # Hafta 2 kaynak denetimi yalnızca beş pilot şehir için hazır.
    # Diğer şehirlerin mevcut API çıktısı değişmeden kalır.
    pilot_sehirler = {1, 8, 24, 39, 82}
    kontrol = {}
    if destination_id in pilot_sehirler:
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
            "average_price": y.ortalama_ucret
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
                # Konumun DB'de olması giriş noktasının doğrulandığı anlamına gelmez.
                "entrance_coordinates_verified": False
            })
        sonuc.append(yer)
    return sonuc


@app.get("/recommendations")
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

@app.get("/map/places")
def get_map_places(city_id: int):
    db = SessionLocal()

    try:
        # Önce doğrulanmış koordinatları getir.
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

        # Aday koordinatları ayrı getir.
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
       

