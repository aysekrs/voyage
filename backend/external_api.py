from fastapi import APIRouter, Query, HTTPException
from rapidapi_service import search_real_flights, find_airport
from rapidapi_service import search_real_hotels, find_hotel_destination
from datetime import date as Date
import httpx
router = APIRouter(prefix="/external", tags=["External APIs"])


# Sahte uçuş verileri
@router.get("/flights")
def get_flights(
    origin: str = Query(..., min_length=3),
    destination: str = Query(..., min_length=3),
    date: str = Query(...)
):
    return {
        "data_source": "mock",
        "flights": [
            {
                "airline": "Turkish Airlines",
                "from_airport": origin.upper(),
                "to_airport": destination.upper(),
                "departure_time": f"{date}T08:00:00",
                "arrival_time": f"{date}T09:30:00",
                "price_per_person": 1850.00,
                "currency": "TRY"
            },
            {
                "airline": "Pegasus",
                "from_airport": origin.upper(),
                "to_airport": destination.upper(),
                "departure_time": f"{date}T14:00:00",
                "arrival_time": f"{date}T15:30:00",
                "price_per_person": 1450.00,
                "currency": "TRY"
            }
        ]
    }


# Sahte otel verileri
@router.get("/hotels")
def get_hotels(
    destination: str = Query(..., min_length=2),
    nights: int = Query(..., ge=1)
):
    return {
        "data_source": "mock",
        "destination": destination,
        "nights": nights,
        "hotels": [
            {
                "hotel_name": "Voyage Comfort Hotel",
                "stars": 3,
                "nightly_price": 1750.00,
                "total_price": 1750.00 * nights,
                "currency": "TRY"
            },
            {
                "hotel_name": "Voyage Premium Hotel",
                "stars": 5,
                "nightly_price": 3200.00,
                "total_price": 3200.00 * nights,
                "currency": "TRY"
            }
        ]
    }

# Sahte döviz kuru verileri
@router.get("/exchange")
def get_exchange_rate(
    from_currency: str = Query(..., min_length=3, max_length=3),
    to_currency: str = Query(..., min_length=3, max_length=3),
    amount: float = Query(1, gt=0)
):
    # Tamamen temsili test kurları
    mock_rates_to_try = {
        "TRY": 1.0,
        "USD": 45.0,
        "EUR": 52.0,
        "GBP": 60.0
    }

    source = from_currency.upper()
    target = to_currency.upper()

    if source not in mock_rates_to_try or target not in mock_rates_to_try:
        raise HTTPException(
            status_code=400,
            detail="Desteklenmeyen para birimi"
        )

    converted_amount = (
        amount * mock_rates_to_try[source]
        / mock_rates_to_try[target]
    )

    return {
        "data_source": "mock",
        "from_currency": source,
        "to_currency": target,
        "amount": amount,
        "converted_amount": round(converted_amount, 2),
        "exchange_rate": round(
            mock_rates_to_try[source] / mock_rates_to_try[target], 6
        )
    }




@router.get("/flights/real")
async def get_real_flights(
    origin: str = Query("IST", min_length=3, max_length=3),
    destination: str = Query("AYT", min_length=3, max_length=3),
    date: str = Query("2026-12-10")
):
    origin = origin.upper()
    destination = destination.upper()

    try:
        # Havalimanlarının gerçek ID'lerini otomatik bul
        origin_airport = await find_airport(origin)
        destination_airport = await find_airport(destination)

        # Gerçek uçuş API'sini çağır
        result = await search_real_flights(
            origin_sky_id=origin_airport["sky_id"],
            destination_sky_id=destination_airport["sky_id"],
            origin_entity_id=origin_airport["entity_id"],
            destination_entity_id=destination_airport["entity_id"],
            flight_date=date
        )

        if result.get("status_code") != 200 or result.get("status") is not True:
            raise ValueError("Gerçek uçuş API'si başarısız.")

        itineraries = (result.get("data") or {}).get("itineraries", [])
        flights = []

        for item in itineraries:
            legs = item.get("legs") or []
            if not legs:
                continue

            leg = legs[0]

            if (
                leg.get("origin", {}).get("displayCode") != origin
                or leg.get("destination", {}).get("displayCode") != destination
            ):
                continue

            flights.append({
                "price": item.get("price", {}).get("formatted"),
                "origin": origin,
                "destination": destination,
                "departure": leg.get("departure"),
                "arrival": leg.get("arrival"),
                "stops": leg.get("stopCount")
            })

        if not flights:
            raise ValueError("Uygun uçuş bulunamadı.")

        return {
            "data_source": "real",
            "flights": flights
        }

    except Exception as e:
        print("GERÇEK UÇUŞ HATASI:", type(e).__name__, str(e))
        mock_result = get_flights(
            origin=origin,
            destination=destination,
            date=date
        )

        return {
            "data_source": "mock",
            "fallback": True,
            "message": "Gerçek uçuş verilerine ulaşılamadı. Örnek veriler gösteriliyor.",
            "flights": mock_result["flights"]
        }


@router.get("/hotels/real")
async def get_real_hotels(
    destination: str = Query("Antalya", min_length=2),
    check_in: Date = Query(Date(2026, 12, 10)),
    check_out: Date = Query(Date(2026, 12, 13)),
    adults: int = Query(2, ge=1, le=20)
):
    if check_out <= check_in:
        raise HTTPException(
            status_code=422,
            detail="Çıkış tarihi giriş tarihinden sonra olmalıdır."
        )

    nights = (check_out - check_in).days

    try:
        destination_id = await find_hotel_destination(destination)

        result = await search_real_hotels(
            destination_id=destination_id,
            check_in=check_in.isoformat(),
            check_out=check_out.isoformat(),
            adults=adults
        )

        if result.get("status_code") != 200 or result.get("status") is not True:
            raise ValueError("Gerçek otel API'si başarısız.")

        hotels_data = (result.get("data") or {}).get("hotels") or []
        hotels = []

        for item in hotels_data:
            property_data = item.get("property") or {}
            gross_price = (
                (property_data.get("priceBreakdown") or {})
                .get("grossPrice") or {}
            )

            if not property_data.get("name") or gross_price.get("value") is None:
                continue

            hotels.append({
                "hotel_name": property_data.get("name"),
                "stars": property_data.get("propertyClass"),
                "total_price": round(float(gross_price["value"]), 2),
                "nightly_price": round(float(gross_price["value"]) / nights, 2),
                "currency": gross_price.get("currency"),
                "image_url": (property_data.get("photoUrls") or [None])[0]
            })

        if not hotels:
            raise ValueError("Uygun otel bulunamadı.")

        return {
            "data_source": "real",
            "destination": destination,
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "nights": nights,
            "adults": adults,
            "hotels": hotels
        }

    except Exception:
        mock_result = get_hotels(
            destination=destination,
            nights=nights
        )

        return {
            "data_source": "mock",
            "fallback": True,
            "message": "Gerçek otel verilerine ulaşılamadı. Örnek veriler gösteriliyor.",
            "destination": destination,
            "nights": nights,
            "hotels": mock_result["hotels"]
        }


@router.get("/exchange/real")
async def get_real_exchange_rate(
    from_currency: str = Query(..., min_length=3, max_length=3),
    to_currency: str = Query(..., min_length=3, max_length=3),
    amount: float = Query(1, gt=0)
):
    source = from_currency.upper()
    target = to_currency.upper()

    if source == target:
        return {
            "data_source": "real",
            "from_currency": source,
            "to_currency": target,
            "amount": amount,
            "exchange_rate": 1.0,
            "converted_amount": round(amount, 2)
        }

    try:
        url = f"https://api.frankfurter.dev/v2/rate/{source}/{target}"

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        rate = float(data["rate"])

        return {
            "data_source": "real",
            "from_currency": source,
            "to_currency": target,
            "amount": amount,
            "exchange_rate": rate,
            "converted_amount": round(amount * rate, 2),
            "date": data.get("date")
        }

    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        mock_result = get_exchange_rate(
            from_currency=source,
            to_currency=target,
            amount=amount
        )

        return {
            **mock_result,
            "data_source": "mock",
            "fallback": True,
            "message": "Gerçek döviz kuruna ulaşılamadı. Örnek kur kullanılıyor."
        }
