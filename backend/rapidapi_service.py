
import os
import httpx
from dotenv import load_dotenv

load_dotenv()



async def test_flight_api():
    url = (
        "https://sky-scrapper.p.rapidapi.com"
        "/api/v1/flights/getNearByAirports"
    )

    headers = {
        "X-RapidAPI-Key": os.getenv("FLIGHT_API_KEY", ""),
        "X-RapidAPI-Host": os.getenv("FLIGHT_API_HOST", "")
    }

    # İstanbul koordinatları
    params = {
        "lat": 41.0082,
        "lng": 28.9784
    }

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            url,
            headers=headers,
            params=params
        )

        data = response.json()

        return {
            "status_code": response.status_code,
            "status": data.get("status"),
            "message": data.get("message"),
            "data": data.get("data")
        }

async def test_hotel_api():
    url = (
        "https://booking-com15.p.rapidapi.com"
        "/api/v1/hotels/searchDestination"
    )

    headers = {
        "X-RapidAPI-Key": os.getenv("HOTEL_API_KEY", ""),
        "X-RapidAPI-Host": os.getenv("HOTEL_API_HOST", "")
    }

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            url,
            headers=headers,
            params={"query": "Madrid"}
        )
        return {
            "status_code": response.status_code,
            "response": response.json()
        }



async def search_real_flights(
    origin_sky_id="IST",
    destination_sky_id="AYT",
    origin_entity_id="95673323",
    destination_entity_id="95673612",
    flight_date="2026-12-10"
):
    url = (
        "https://sky-scrapper.p.rapidapi.com"
        "/api/v1/flights/searchFlights"
    )

    headers = {
        "X-RapidAPI-Key": os.getenv("FLIGHT_API_KEY", ""),
        "X-RapidAPI-Host": os.getenv("FLIGHT_API_HOST", "")
    }

    params = {
        "originSkyId": origin_sky_id,
        "destinationSkyId": destination_sky_id,
        "originEntityId": origin_entity_id,
        "destinationEntityId": destination_entity_id,
        "date": flight_date,
        "adults": 1,
        "currency": "TRY",
        "market": "TR",
        "countryCode": "TR"
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            url,
            headers=headers,
            params=params
        )

        print("UÇUŞ API HTTP DURUMU:", response.status_code)

        if response.status_code != 200:
            print("UÇUŞ API HATASI:", response.text[:1000])

        response.raise_for_status()

        data = response.json()

        print("UÇUŞ API STATUS:", data.get("status"))
        print("UÇUŞ API MESSAGE:", data.get("message"))

        return {
            "status_code": response.status_code,
            "status": data.get("status"),
            "message": data.get("message"),
            "data": data.get("data")
        }


async def search_real_hotel_destination(city="Antalya"):
    url = (
        "https://booking-com15.p.rapidapi.com"
        "/api/v1/hotels/searchDestination"
    )

    headers = {
        "X-RapidAPI-Key": os.getenv("HOTEL_API_KEY", ""),
        "X-RapidAPI-Host": os.getenv("HOTEL_API_HOST", "")
    }

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            url,
            headers=headers,
            params={"query": city}
        )

        response.raise_for_status()
        data = response.json()

        if data.get("status") is not True:
            raise ValueError("Otel destinasyon sorgusu başarısız.")

        destinations = data.get("data") or []

        cities = [
            item for item in destinations
            if item.get("search_type") == "city"
        ]

        return {
            "city": city,
            "destinations": [
                {
                    "name": item.get("name"),
                    "dest_id": item.get("dest_id"),
                    "search_type": item.get("search_type")
                }
                for item in cities
            ]
        }


async def search_real_hotels(
    destination_id="-735347",
    check_in="2026-12-10",
    check_out="2026-12-13",
    adults=2
):
    url = (
        "https://booking-com15.p.rapidapi.com"
        "/api/v1/hotels/searchHotels"
    )

    headers = {
        "X-RapidAPI-Key": os.getenv("HOTEL_API_KEY", ""),
        "X-RapidAPI-Host": os.getenv("HOTEL_API_HOST", "")
    }

    params = {
        "dest_id": destination_id,
        "search_type": "CITY",
        "arrival_date": check_in,
        "departure_date": check_out,
        "adults": adults,
        "room_qty": 1,
        "page_number": 1,
        "currency_code": "TRY"
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            url,
            headers=headers,
            params=params
        )
        response.raise_for_status()
        data = response.json()

    return {
        "status_code": response.status_code,
        "status": data.get("status"),
        "message": data.get("message"),
        "data": data.get("data")
    }

    
async def find_airport(airport_code: str):
    url = (
        "https://sky-scrapper.p.rapidapi.com"
        "/api/v1/flights/searchAirport"
    )

    headers = {
        "X-RapidAPI-Key": os.getenv("FLIGHT_API_KEY", ""),
        "X-RapidAPI-Host": os.getenv("FLIGHT_API_HOST", "")
    }

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            url,
            headers=headers,
            params={"query": airport_code.upper()}
        )
        response.raise_for_status()
        data = response.json()

    if data.get("status") is not True:
        raise ValueError("Havalimanı araması başarısız.")

    for airport in data.get("data") or []:
        navigation = airport.get("navigation") or {}
        flight_params = navigation.get("relevantFlightParams") or {}

        if (
            flight_params.get("skyId") == airport_code.upper()
            and navigation.get("entityType") == "AIRPORT"
        ):
            return {
                "sky_id": flight_params["skyId"],
                "entity_id": navigation["entityId"]
            }

    raise ValueError(f"Havalimanı bulunamadı: {airport_code}")

async def find_hotel_destination(city: str):
    url = (
        "https://booking-com15.p.rapidapi.com"
        "/api/v1/hotels/searchDestination"
    )

    headers = {
        "X-RapidAPI-Key": os.getenv("HOTEL_API_KEY", ""),
        "X-RapidAPI-Host": os.getenv("HOTEL_API_HOST", "")
    }

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            url,
            headers=headers,
            params={"query": city}
        )
        response.raise_for_status()
        data = response.json()

    if data.get("status") is not True:
        raise ValueError("Otel destinasyon araması başarısız.")

    destinations = data.get("data") or []

    # Öncelikle tam şehir eşleşmesini bul
    for item in destinations:
        if (
            item.get("search_type", "").lower() == "city"
            and item.get("name", "").casefold() == city.casefold()
        ):
            return item["dest_id"]

    raise ValueError(f"Şehir bulunamadı: {city}")

