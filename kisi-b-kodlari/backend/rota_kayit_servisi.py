"""VoyageAI - 4. hafta: üretilmiş rotayı PostgreSQL'e kaydetme ve geri çağırma.

Tablolar: itineraries, itinerary_stops -> once sql/hafta4_itineraries.sql calistirilmali.
Yalnızca `yerler` tablosundaki koordinatlarla hesaplanan rotayı kaydeder.
Kullanıcı kimliği/erişim yetkisi henüz olmadığı için geliştirme/test amaçlıdır.
"""

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from database import SessionLocal
from rota_servisi import get_destination_route

router = APIRouter(tags=["Kaydedilen Rotalar"])


@router.post("/itineraries", status_code=201)
def rota_kaydet(
    destination_id: int = Query(..., ge=1),
    days: int = Query(3, ge=1, le=7),
    hours_per_day: int = Query(5, ge=1, le=12),
):
    # Aynı algoritmayı kullan: kullanıcı tarafından gönderilen koordinatları kabul etme.
    # include_candidates acikca False verilmeli: fonksiyon dogrudan cagrildiginda
    # varsayilan deger Query(...) nesnesidir ve "dogru" sayilir (test modu acilirdi).
    rota = get_destination_route(
        destination_id=destination_id, days=days, hours_per_day=hours_per_day,
        include_candidates=False,
    )
    if rota["routed_places"] == 0:
        raise HTTPException(
            status_code=400,
            detail="Kaydedilecek durak bulunamadi. Ana tabloda kullanilabilir koordinat gerekli.",
        )

    db = SessionLocal()
    try:
        kayit_id = db.execute(
            text("""
                INSERT INTO itineraries
                    (sehir_id, gun_sayisi, gunluk_saat, toplam_mesafe_km,
                     toplam_yol_dk, algorithm, version)
                VALUES
                    (:sehir_id, :gun_sayisi, :gunluk_saat, :toplam_mesafe_km,
                     :toplam_yol_dk, :algorithm, 1)
                RETURNING itinerary_id
            """),
            {
                "sehir_id": destination_id,
                "gun_sayisi": days,
                "gunluk_saat": hours_per_day,
                "toplam_mesafe_km": rota["total_distance_km"],
                "toplam_yol_dk": rota["total_travel_minutes"],
                "algorithm": rota["algorithm"],
            },
        ).scalar_one()

        for gun in rota["itinerary"]:
            for durak in gun["places"]:
                db.execute(
                    text("""
                        INSERT INTO itinerary_stops
                            (itinerary_id, yer_id, gun_no, sira,
                             ziyaret_suresi, onceki_duraktan_km, yol_suresi_dk)
                        VALUES
                            (:itinerary_id, :yer_id, :gun_no, :sira,
                             :ziyaret_suresi, :onceki_duraktan_km, :yol_suresi_dk)
                    """),
                    {
                        "itinerary_id": kayit_id,
                        "yer_id": durak["place_id"],
                        "gun_no": gun["day"],
                        "sira": durak["order"],
                        "ziyaret_suresi": durak["visit_minutes"],
                        "onceki_duraktan_km": durak["distance_from_previous_km"],
                        "yol_suresi_dk": durak["travel_minutes"],
                    },
                )

        db.commit()
        return {
            "message": "Rota kaydedildi",
            "itinerary_id": kayit_id,
            "city": rota["city"],
            "days": days,
            "hours_per_day": hours_per_day,
            "routed_places": rota["routed_places"],
            "total_distance_km": rota["total_distance_km"],
            "total_travel_minutes": rota["total_travel_minutes"],
            "coordinate_source": "yerler",
        }
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Rota kaydedilemedi. Veritabani loglarini kontrol edin.")
    finally:
        db.close()


@router.get("/itineraries/{itinerary_id}")
def kayitli_rotayi_getir(itinerary_id: int):
    db = SessionLocal()
    try:
        plan = db.execute(
            text("""
                SELECT i.itinerary_id, i.sehir_id, s.ad AS sehir,
                       i.gun_sayisi, i.gunluk_saat,
                       i.toplam_mesafe_km, i.olusturulma_tarihi,
                       i.toplam_yol_dk, i.algorithm
                FROM itineraries i
                JOIN sehirler s ON s.sehir_id = i.sehir_id
                WHERE i.itinerary_id = :id
            """),
            {"id": itinerary_id},
        ).mappings().first()
        if plan is None:
            raise HTTPException(status_code=404, detail="Kayitli rota bulunamadi.")

        duraklar = db.execute(
            text("""
                SELECT st.gun_no, st.sira, st.yer_id,
                       y.ad AS yer_adi, y.kategori,
                       y.enlem, y.boylam,
                       st.ziyaret_suresi, st.onceki_duraktan_km,
                       st.yol_suresi_dk
                FROM itinerary_stops st
                JOIN yerler y ON y.yer_id = st.yer_id
                WHERE st.itinerary_id = :id
                ORDER BY st.gun_no, st.sira
            """),
            {"id": itinerary_id},
        ).mappings().all()

        gunler = [
            {"day": n, "places": [], "visit_minutes": 0, "travel_minutes": 0, "distance_km": 0.0}
            for n in range(1, plan["gun_sayisi"] + 1)
        ]
        for d in duraklar:
            gun = gunler[d["gun_no"] - 1]
            gun["places"].append({
                "order": d["sira"],
                "place_id": d["yer_id"],
                "name": d["yer_adi"],
                "category": d["kategori"],
                "latitude": d["enlem"],
                "longitude": d["boylam"],
                "visit_minutes": d["ziyaret_suresi"],
                "distance_from_previous_km": d["onceki_duraktan_km"],
                "travel_minutes": d["yol_suresi_dk"] or 0,
            })
            gun["visit_minutes"] += d["ziyaret_suresi"]
            gun["travel_minutes"] += d["yol_suresi_dk"] or 0
            gun["distance_km"] += float(d["onceki_duraktan_km"] or 0)
        for gun in gunler:
            gun["distance_km"] = round(gun["distance_km"], 3)
            gun["total_minutes"] = gun["visit_minutes"] + gun["travel_minutes"]

        return {
            "itinerary_id": plan["itinerary_id"],
            "destination_id": plan["sehir_id"],
            "city": plan["sehir"],
            "days": plan["gun_sayisi"],
            "hours_per_day": plan["gunluk_saat"],
            "total_distance_km": plan["toplam_mesafe_km"],
            "total_travel_minutes": plan["toplam_yol_dk"],
            "algorithm": plan["algorithm"],
            "created_at": plan["olusturulma_tarihi"].isoformat(),
            "routed_places": len(duraklar),
            "coordinate_source": "yerler",
            "itinerary": gunler,
        }
    finally:
        db.close()
