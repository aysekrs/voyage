
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from database import SessionLocal
from city_models import Sehir, Yer
from rota_algoritmasi import rota_olustur, haversine

router = APIRouter()


@router.get("/destinations/{destination_id}/route")
def get_destination_route(
    destination_id: int,
    days: int = Query(3, ge=1, le=7),
    hours_per_day: int = Query(5, ge=1, le=12)
):
    db = SessionLocal()

    try:
        sehir = db.get(Sehir, destination_id)

        if sehir is None:
            raise HTTPException(
                status_code=404,
                detail="Sehir bulunamadi."
            )

        yerler = db.execute(
            select(Yer)
            .where(Yer.sehir_id == destination_id)
            .order_by(Yer.yer_id)
        ).scalars().all()

        uygun_yerler = []
        koordinatsiz = 0
        suresiz = 0

        for yer in yerler:
            if yer.enlem is None or yer.boylam is None:
                koordinatsiz += 1
                continue

            if yer.ziyaret_suresi is None or yer.ziyaret_suresi <= 0:
                suresiz += 1
                continue

            if not (
                -90 <= yer.enlem <= 90
                and -180 <= yer.boylam <= 180
            ):
                koordinatsiz += 1
                continue

            uygun_yerler.append({
                "id": yer.yer_id,
                "ad": yer.ad,
                "kategori": yer.kategori,
                "lat": yer.enlem,
                "lon": yer.boylam,
                "ziyaret_suresi": yer.ziyaret_suresi
            })

        # Her günün kapasitesi dakika cinsinden.
        gunluk_limit = hours_per_day * 60

        gunler = [
            {
                "day": i + 1,
                "places": [],
                "visit_minutes": 0
            }
            for i in range(days)
        ]

        sigmayan_yerler = []

        # Bir yeri yalnızca bir güne ekle.
        for yer in uygun_yerler:
            yerlestirildi = False

            for gun in gunler:
                if (
                    gun["visit_minutes"]
                    + yer["ziyaret_suresi"]
                    <= gunluk_limit
                ):
                    gun["places"].append(yer)
                    gun["visit_minutes"] += yer["ziyaret_suresi"]
                    yerlestirildi = True
                    break

            if not yerlestirildi:
                sigmayan_yerler.append(yer["id"])

        toplam_mesafe = 0.0

        # Her günün durak sırasını ayrı optimize et.
        for gun in gunler:
            sonuc = rota_olustur(gun["places"])
            sirali_yerler = sonuc["rota"]

            duraklar = []
            onceki = None

            for sira, yer in enumerate(sirali_yerler, 1):
                mesafe_km = 0.0

                if onceki is not None:
                    mesafe_km = haversine(
                        onceki["lat"],
                        onceki["lon"],
                        yer["lat"],
                        yer["lon"]
                    )

                duraklar.append({
                    "order": sira,
                    "place_id": yer["id"],
                    "name": yer["ad"],
                    "category": yer["kategori"],
                    "latitude": yer["lat"],
                    "longitude": yer["lon"],
                    "visit_minutes": yer["ziyaret_suresi"],
                    "distance_from_previous_km": round(
                        mesafe_km, 3
                    )
                })

                onceki = yer

            gun["places"] = duraklar
            gun["distance_km"] = sonuc["son_mesafe_km"]
            gun["distance_before_2opt_km"] = sonuc["ilk_mesafe_km"]

            toplam_mesafe += sonuc["son_mesafe_km"]

        return {
            "destination_id": destination_id,
            "city": sehir.ad,
            "country": sehir.ulke,
            "days": days,
            "hours_per_day": hours_per_day,
            "algorithm": "nearest_neighbor + 2-opt",
            "distance_type": "straight_line",
            "coordinate_source": "yerler",
            "total_distance_km": round(toplam_mesafe, 3),
            "routed_places": sum(
                len(gun["places"]) for gun in gunler
            ),
            "excluded": {
                "missing_or_invalid_coordinates": koordinatsiz,
                "missing_visit_duration": suresiz,
                "not_fitting_in_days": len(sigmayan_yerler)
            },
            "itinerary": gunler,
            "warning": (
                "Bu rota kus ucusu mesafe kullanir. "
                "Gercek yol, ulasim ve mola surelerini icermez."
            )
        }

    finally:
        db.close()
