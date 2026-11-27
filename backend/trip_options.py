"""5. Hafta: tüm aday şehirler için maliyet + puan hesabı (trip_options).

Endpoint'ler:
    POST /trips/{trip_id}/options              -> hesapla, kaydet, sıralı listeyi dön
    GET  /trips/{trip_id}/options              -> kayıtlı sonuçları dön
    POST /trips/{trip_id}/options/{id}/select  -> "Bu şehri seç"

main.py'deki conn() ve current_user() fonksiyonlarını kullanır; döngüsel
import olmasın diye bunlar register() ile içeri verilir.
"""

from datetime import datetime, time, timezone
from decimal import Decimal

import httpx
from fastapi import Cookie, HTTPException, Path

import cost_calculator as cc
from external_api import get_exchange_rate
from rota_servisi import get_destination_route

# Aday sayılmak için şehirde en az bu kadar yer olmalı
MIN_YER_SAYISI = 1

# Rota hesabında günde gezilen saat
GUNLUK_GEZI_SAATI = 5

# Kayıtlı uçuş/otel yoksa kullanılan sahte fiyatlar (TL, kişi başı / gecelik)
SAHTE_FIYAT = {
    "yurt_ici": {"ucus": 1450.0, "otel": 1750.0},
    "yurt_disi": {"ucus": 4500.0, "otel": 3000.0},
}

# yerler.kategori değerleri -> ilgi alanları
KATEGORI_ALAN = {
    "doğa": "nature",
    "yemek": "food",
    "tarih": "history",
    "gece_hayati": "nightlife",
}


# ---------------------------------------------------------------
# Döviz: önce gerçek kur, olmazsa 4. haftadaki sahte kur
# ---------------------------------------------------------------

class KurCevirici:
    def __init__(self):
        self._kurlar = {"TRY": 1.0}

    def kur(self, para_birimi: str | None) -> float:
        kod = (para_birimi or "TRY").upper()
        if kod in self._kurlar:
            return self._kurlar[kod]
        try:
            cevap = httpx.get(
                f"https://api.frankfurter.dev/v2/rate/{kod}/TRY", timeout=5
            )
            cevap.raise_for_status()
            oran = float(cevap.json()["rate"])
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            try:
                oran = get_exchange_rate(
                    from_currency=kod, to_currency="TRY", amount=1
                )["exchange_rate"]
            except HTTPException:
                raise HTTPException(422, f"{kod} para birimi TL'ye çevrilemiyor.")
        self._kurlar[kod] = oran
        return oran

    def tl(self, tutar, para_birimi: str | None) -> float:
        if tutar is None:
            return 0.0
        return round(float(tutar) * self.kur(para_birimi), 2)


def _f(deger):
    return float(deger) if isinstance(deger, Decimal) else deger


# ---------------------------------------------------------------
# Yardımcı sorgular
# ---------------------------------------------------------------

def _seyahat_ve_tercih(db, trip_id: int, user_id: int, sadece_sahip: bool):
    rol_kosulu = "AND tm.role = 'owner'" if sadece_sahip else ""
    satir = db.execute(
        f"""
        SELECT t.id, t.start_date, t.end_date, t.budget_try, t.people_count,
               t.origin_airport_code, t.selected_destination_id,
               tp.nature_weight, tp.food_weight, tp.history_weight,
               tp.nightlife_weight
        FROM trips t
        JOIN trip_members tm ON tm.trip_id = t.id AND tm.user_id = %s {rol_kosulu}
        LEFT JOIN trip_preferences tp ON tp.trip_id = t.id
        WHERE t.id = %s
        """,
        (user_id, trip_id),
    ).fetchone()
    if not satir:
        raise HTTPException(404, "Seyahat bulunamadı veya yetkiniz yok.")
    return satir


def _aday_sehirler(db, origin_airport_code: str | None):
    """En az MIN_YER_SAYISI yeri olan şehirler, kalkış şehri hariç.
    Kategori sayıları da gelir. (Koordinatı/süresi eksik yerler rotaya
    girmez, sadece aktivite maliyetine katılmaz.)"""
    return db.execute(
        """
        SELECT s.sehir_id, s.ad, s.ulke, s.havalimani_kodu, s.para_birimi,
               s.doga_puani, s.yemek_puani, s.tarih_puani, s.gece_hayati_puani,
               s.gunluk_yemek_maliyeti,
               COUNT(y.yer_id) AS yer_sayisi,
               COUNT(*) FILTER (WHERE y.kategori = 'doğa') AS doga_sayisi,
               COUNT(*) FILTER (WHERE y.kategori = 'yemek') AS yemek_sayisi,
               COUNT(*) FILTER (WHERE y.kategori = 'tarih') AS tarih_sayisi,
               COUNT(*) FILTER (WHERE y.kategori = 'gece_hayati') AS gece_sayisi
        FROM sehirler s
        JOIN yerler y ON y.sehir_id = s.sehir_id
        WHERE s.havalimani_kodu IS DISTINCT FROM %s
        GROUP BY s.sehir_id
        HAVING COUNT(y.yer_id) >= %s
        ORDER BY s.sehir_id
        """,
        ((origin_airport_code or "").upper(), MIN_YER_SAYISI),
    ).fetchall()


def _sehir_puanlari(sehir) -> dict:
    kayitli = {
        "nature": sehir["doga_puani"],
        "food": sehir["yemek_puani"],
        "history": sehir["tarih_puani"],
        "nightlife": sehir["gece_hayati_puani"],
    }
    if all(v is not None for v in kayitli.values()):
        return {k: _f(v) for k, v in kayitli.items()}
    # Puanlar henüz girilmemiş: yer kategorilerinden üret
    return cc.kategori_sayilarindan_puan({
        "nature": sehir["doga_sayisi"],
        "food": sehir["yemek_sayisi"],
        "history": sehir["tarih_sayisi"],
        "nightlife": sehir["gece_sayisi"],
    })


def _bolge(sehir) -> str:
    return "yurt_ici" if (sehir["ulke"] or "").strip() == "Türkiye" else "yurt_disi"


def _en_ucuz_ucus(db, kur, trip, sehir, yon: str):
    """Seyahat + şehir için kayıtlı en ucuz uçuş. Yoksa sahte uçuş eklenir
    (trip_options'ın bağlanacağı bir flights satırı olsun diye)."""
    ucuslar = db.execute(
        """
        SELECT id, price_per_person, currency FROM flights
        WHERE trip_id = %s AND destination_id = %s AND direction = %s
          AND price_per_person IS NOT NULL
        """,
        (trip["id"], sehir["sehir_id"], yon),
    ).fetchall()
    if ucuslar:
        en_ucuz = min(ucuslar, key=lambda u: kur.tl(u["price_per_person"], u["currency"]))
        return en_ucuz["id"], kur.tl(en_ucuz["price_per_person"], en_ucuz["currency"])

    fiyat = SAHTE_FIYAT[_bolge(sehir)]["ucus"]
    gidis = yon == "outbound"
    tarih = trip["start_date"] if gidis else trip["end_date"]
    kalkis = datetime.combine(tarih, time(10, 0), tzinfo=timezone.utc)
    yeni = db.execute(
        """
        INSERT INTO flights (trip_id, destination_id, direction, airline,
                             from_airport, to_airport, departure_time,
                             price_per_person, currency, data_source)
        VALUES (%s, %s, %s, 'Örnek Havayolu', %s, %s, %s, %s, 'TRY', 'mock')
        RETURNING id
        """,
        (
            trip["id"], sehir["sehir_id"], yon,
            trip["origin_airport_code"] if gidis else sehir["havalimani_kodu"],
            sehir["havalimani_kodu"] if gidis else trip["origin_airport_code"],
            kalkis, fiyat,
        ),
    ).fetchone()
    return yeni["id"], fiyat


def _en_ucuz_otel(db, kur, trip, sehir):
    oteller = db.execute(
        """
        SELECT id, nightly_price, currency FROM accommodations
        WHERE trip_id = %s AND destination_id = %s AND nightly_price IS NOT NULL
        """,
        (trip["id"], sehir["sehir_id"]),
    ).fetchall()
    if oteller:
        en_ucuz = min(oteller, key=lambda o: kur.tl(o["nightly_price"], o["currency"]))
        return en_ucuz["id"], kur.tl(en_ucuz["nightly_price"], en_ucuz["currency"])

    fiyat = SAHTE_FIYAT[_bolge(sehir)]["otel"]
    yeni = db.execute(
        """
        INSERT INTO accommodations (trip_id, destination_id, hotel_name, stars,
                                    nightly_price, currency, data_source)
        VALUES (%s, %s, %s, 3, %s, 'TRY', 'mock')
        RETURNING id
        """,
        (trip["id"], sehir["sehir_id"], f"{sehir['ad']} Örnek Otel", fiyat),
    ).fetchone()
    return yeni["id"], fiyat


def _rotadaki_ucretler(db, kur, sehir, gun: int) -> list:
    """B'nin rota servisiyle gün sayısı kadar rota çıkar, duraklardaki
    yerlerin ortalama ücretlerini TL olarak dön.

    Ücretin para birimi yerler.fiyat_para_birimi'nden okunur (EUR, TRY...);
    boşsa şehrin para birimi kullanılır. Ücreti boş olan yer 0 sayılır.
    """
    rota = get_destination_route(
        destination_id=sehir["sehir_id"], days=gun, hours_per_day=GUNLUK_GEZI_SAATI
    )
    yer_idleri = [
        durak["place_id"]
        for gun_plani in rota["itinerary"]
        for durak in gun_plani["places"]
    ]
    if not yer_idleri:
        return []
    satirlar = db.execute(
        """
        SELECT ortalama_ucret, fiyat_para_birimi
        FROM yerler
        WHERE yer_id = ANY(%s) AND ortalama_ucret IS NOT NULL
        """,
        (yer_idleri,),
    ).fetchall()
    return [
        kur.tl(s["ortalama_ucret"], s["fiyat_para_birimi"] or sehir["para_birimi"])
        for s in satirlar
    ]


def _sonuclari_getir(db, trip_id: int):
    return db.execute(
        """
        SELECT o.*, s.ad AS city, s.ulke AS country,
               (o.destination_id = t.selected_destination_id) AS is_selected
        FROM trip_options o
        JOIN sehirler s ON s.sehir_id = o.destination_id
        JOIN trips t ON t.id = o.trip_id
        WHERE o.trip_id = %s
        ORDER BY o.overall_score DESC, o.total_cost ASC
        """,
        (trip_id,),
    ).fetchall()


# ---------------------------------------------------------------
# Endpoint'ler
# ---------------------------------------------------------------

def register(app, conn, current_user):

    @app.post("/trips/{trip_id}/options", tags=["Trip options"])
    def hesapla(
        trip_id: int = Path(gt=0),
        voyage_session: str | None = Cookie(default=None),
    ):
        payload, _ = current_user(voyage_session)
        user_id = int(payload["sub"])
        kur = KurCevirici()

        with conn() as db:
            with db.transaction():
                trip = _seyahat_ve_tercih(db, trip_id, user_id, sadece_sahip=True)

                if trip["nature_weight"] is None:
                    raise HTTPException(422, "Seyahatin ilgi alanı ağırlıkları girilmemiş.")
                if not trip["budget_try"] or not trip["people_count"]:
                    raise HTTPException(422, "Seyahatin bütçesi ve kişi sayısı girilmemiş.")

                agirliklar = {
                    "nature": trip["nature_weight"],
                    "food": trip["food_weight"],
                    "history": trip["history_weight"],
                    "nightlife": trip["nightlife_weight"],
                }
                butce = float(trip["budget_try"])
                kisi = trip["people_count"]
                gun = cc.gun_sayisi(trip["start_date"], trip["end_date"])

                adaylar = _aday_sehirler(db, trip["origin_airport_code"])
                if not adaylar:
                    raise HTTPException(422, "Hesaplanacak aday şehir bulunamadı.")

                db.execute("DELETE FROM trip_options WHERE trip_id = %s", (trip_id,))

                for sehir in adaylar:
                    gidis_id, gidis_tl = _en_ucuz_ucus(db, kur, trip, sehir, "outbound")
                    donus_id, donus_tl = _en_ucuz_ucus(db, kur, trip, sehir, "return")
                    otel_id, gecelik_tl = _en_ucuz_otel(db, kur, trip, sehir)

                    maliyet = cc.maliyet_hesapla(
                        gidis_kisi_basi_tl=gidis_tl,
                        donus_kisi_basi_tl=donus_tl,
                        gecelik_fiyat_tl=gecelik_tl,
                        gunluk_yemek_tl=_f(sehir["gunluk_yemek_maliyeti"]),
                        gunluk_ulasim_tl=None,  # sehirler tablosunda henüz yok
                        rotadaki_ucretler_tl=_rotadaki_ucretler(db, kur, sehir, gun),
                        start_date=trip["start_date"],
                        end_date=trip["end_date"],
                        people_count=kisi,
                    )
                    tercih = cc.tercih_puani(agirliklar, _sehir_puanlari(sehir))
                    uyum = cc.butce_uyum_puani(maliyet.total_cost, butce)

                    db.execute(
                        """
                        INSERT INTO trip_options (
                            trip_id, destination_id, outbound_flight_id,
                            return_flight_id, accommodation_id,
                            flight_cost, accommodation_cost, food_cost,
                            activity_cost, local_transport_cost,
                            total_cost, remaining_budget,
                            preference_score, budget_fit_score, overall_score
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s)
                        """,
                        (
                            trip_id, sehir["sehir_id"], gidis_id, donus_id, otel_id,
                            maliyet.flight_cost, maliyet.accommodation_cost,
                            maliyet.food_cost, maliyet.activity_cost,
                            maliyet.local_transport_cost, maliyet.total_cost,
                            round(butce - maliyet.total_cost, 2),
                            tercih, uyum, cc.genel_puan(tercih, uyum),
                        ),
                    )

                sonuclar = _sonuclari_getir(db, trip_id)

        return {"trip_id": trip_id, "budget_try": butce, "options": sonuclar}

    @app.get("/trips/{trip_id}/options", tags=["Trip options"])
    def listele(
        trip_id: int = Path(gt=0),
        voyage_session: str | None = Cookie(default=None),
    ):
        payload, _ = current_user(voyage_session)
        with conn() as db:
            trip = _seyahat_ve_tercih(db, trip_id, int(payload["sub"]), sadece_sahip=False)
            sonuclar = _sonuclari_getir(db, trip_id)
        return {
            "trip_id": trip_id,
            "budget_try": _f(trip["budget_try"]),
            "options": sonuclar,
        }

    @app.post("/trips/{trip_id}/options/{option_id}/select", tags=["Trip options"])
    def sehri_sec(
        trip_id: int = Path(gt=0),
        option_id: int = Path(gt=0),
        voyage_session: str | None = Cookie(default=None),
    ):
        payload, _ = current_user(voyage_session)
        with conn() as db:
            with db.transaction():
                _seyahat_ve_tercih(db, trip_id, int(payload["sub"]), sadece_sahip=True)
                secilen = db.execute(
                    """
                    UPDATE trips t
                    SET selected_destination_id = o.destination_id,
                        destination = s.ad,
                        updated_at = NOW()
                    FROM trip_options o
                    JOIN sehirler s ON s.sehir_id = o.destination_id
                    WHERE o.id = %s AND o.trip_id = %s AND t.id = o.trip_id
                    RETURNING t.id, t.selected_destination_id, t.destination
                    """,
                    (option_id, trip_id),
                ).fetchone()
                if not secilen:
                    raise HTTPException(404, "Bu seyahate ait şehir önerisi bulunamadı.")
        return secilen
