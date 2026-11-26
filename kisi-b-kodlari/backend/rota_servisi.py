from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, text

from database import SessionLocal
from city_models import Sehir, Yer
from rota_algoritmasi import haversine, nearest_neighbor, rota_mesafesi
from rota_planlayici import gunlere_bol, yol_suresi_dk

router = APIRouter()


@router.get('/destinations/{destination_id}/route')
def get_destination_route(
    destination_id: int,
    days: int = Query(3, ge=1, le=7),
    hours_per_day: int = Query(5, ge=1, le=12),
    include_candidates: bool = Query(False, description='Yalnizca test: aday koordinatlari kullan')
):
    db = SessionLocal()
    try:
        sehir = db.get(Sehir, destination_id)
        if sehir is None:
            raise HTTPException(status_code=404, detail='Sehir bulunamadi.')

        yerler = db.execute(
            select(Yer)
            .where(Yer.sehir_id == destination_id)
            .order_by(Yer.yer_id)
        ).scalars().all()

        adaylar = {}
        if include_candidates:
            # Yalnizca koordinat adayi oku; veritabanina YAZMA.
            rows = db.execute(text('''
                SELECT k.yer_id, k.enlem, k.boylam
                FROM koordinat_adaylari k
                JOIN yerler y ON y.yer_id = k.yer_id
                WHERE y.sehir_id = :sehir_id
                  AND k.enlem BETWEEN -90 AND 90
                  AND k.boylam BETWEEN -180 AND 180
            '''), {'sehir_id': destination_id}).all()
            adaylar = {row.yer_id: (row.enlem, row.boylam) for row in rows}

        uygun_yerler = []
        koordinatsiz = 0
        suresiz = 0
        aday_kullanilan = 0

        for yer in yerler:
            lat, lon = yer.enlem, yer.boylam
            ana_gecerli = (
                lat is not None and lon is not None
                and -90 <= lat <= 90 and -180 <= lon <= 180
            )
            aday_mi = False
            if not ana_gecerli and include_candidates and yer.yer_id in adaylar:
                lat, lon = adaylar[yer.yer_id]
                aday_mi = True

            if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
                koordinatsiz += 1
                continue
            if yer.ziyaret_suresi is None or yer.ziyaret_suresi <= 0:
                suresiz += 1
                continue
            if aday_mi:
                aday_kullanilan += 1

            uygun_yerler.append({
                'id': yer.yer_id,
                'ad': yer.ad,
                'kategori': yer.kategori,
                'lat': lat,
                'lon': lon,
                'ziyaret_suresi': yer.ziyaret_suresi,
                'coordinate_status': 'ADAY_DOGRULANMADI' if aday_mi else 'ANA_TABLO'
            })

        gunluk_limit = hours_per_day * 60
        gun_listesi, sigmayan_yerler = gunlere_bol(uygun_yerler, days, gunluk_limit)

        gunler = []
        toplam_mesafe = 0.0
        toplam_yol_dk = 0
        for gun_no, sirali_yerler in enumerate(gun_listesi, 1):
            nn_mesafe = rota_mesafesi(nearest_neighbor(sirali_yerler)) if sirali_yerler else 0.0
            duraklar = []
            onceki = None
            gun_mesafe = 0.0
            gun_yol_dk = 0
            for sira, yer in enumerate(sirali_yerler, 1):
                mesafe_km = 0.0
                if onceki is not None:
                    mesafe_km = haversine(onceki['lat'], onceki['lon'], yer['lat'], yer['lon'])
                yol_dk = yol_suresi_dk(mesafe_km)
                gun_mesafe += mesafe_km
                gun_yol_dk += yol_dk
                duraklar.append({
                    'order': sira,
                    'place_id': yer['id'],
                    'name': yer['ad'],
                    'category': yer['kategori'],
                    'latitude': yer['lat'],
                    'longitude': yer['lon'],
                    'visit_minutes': yer['ziyaret_suresi'],
                    'distance_from_previous_km': round(mesafe_km, 3),
                    'travel_minutes': yol_dk,
                    'coordinate_status': yer['coordinate_status']
                })
                onceki = yer

            ziyaret_dk = sum(y['ziyaret_suresi'] for y in sirali_yerler)
            gunler.append({
                'day': gun_no,
                'places': duraklar,
                'visit_minutes': ziyaret_dk,
                'travel_minutes': gun_yol_dk,
                'total_minutes': ziyaret_dk + gun_yol_dk,
                'distance_km': round(gun_mesafe, 3),
                'distance_before_2opt_km': round(max(nn_mesafe, gun_mesafe), 3),
            })
            toplam_mesafe += gun_mesafe
            toplam_yol_dk += gun_yol_dk

        return {
            'destination_id': destination_id,
            'city': sehir.ad,
            'country': sehir.ulke,
            'days': days,
            'hours_per_day': hours_per_day,
            'algorithm': 'nearest_neighbor + 2-opt (bolgesel gun bolme)',
            'distance_type': 'straight_line',
            'coordinate_source': 'yerler + koordinat_adaylari (TEST)' if include_candidates else 'yerler',
            'test_mode': include_candidates,
            'candidate_places_available': aday_kullanilan,
            'total_distance_km': round(toplam_mesafe, 3),
            'total_travel_minutes': toplam_yol_dk,
            'routed_places': sum(len(gun['places']) for gun in gunler),
            'excluded': {
                'missing_or_invalid_coordinates': koordinatsiz,
                'missing_visit_duration': suresiz,
                'not_fitting_in_days': len(sigmayan_yerler)
            },
            'itinerary': gunler,
            'warning': (
                'TEST MODU: Bazi koordinatlar dogrulanmamis adaylardir. '
                'Gercek ziyaret/giris noktasi olarak kullanmayin. '
                if include_candidates else ''
            ) + 'Mesafeler kus ucusudur. Yol sureleri tahminidir (1.5 km\'ye kadar yuruyus, ustu toplu tasima); gercek yol tarifi degildir.'
        }
    finally:
        db.close()
