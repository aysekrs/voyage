"""VoyageAI - 5. hafta (Kişi B): AI asistan API'si.

GET    /ai/chat     -> açık sohbet (henüz seyahate dönüşmemiş mesajlar) ve son durum
POST   /ai/chat     -> kullanıcı mesajı gönder, asistan cevabı + anlaşılan bilgiler
DELETE /ai/chat     -> açık sohbeti sil (yeni sohbet)
POST   /ai/onayla   -> onay kartındaki (düzeltilmiş) bilgilerle seyahati oluştur

Seyahati A'nın POST /trips kodu oluşturur (aynı kontroller, trip_members ve
trip_preferences kayıtları). Ardından sohbetin mesajlarına trip_id yazılır.
"""
from __future__ import annotations

import json
from datetime import date

from fastapi import APIRouter, Cookie, HTTPException, Request
from pydantic import BaseModel, Field, ValidationError

from ai_cikarim import ALANLAR, baslik_uret, cikar, dogrula, yanit_uret

router = APIRouter(prefix="/ai", tags=["AI asistan"])


def _main():
    # main.py bu dosyayı içe aktardığı için döngüyü önlemek adına geç yükleniyor.
    import main
    return main


class MesajGirdisi(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class OnayGirdisi(BaseModel):
    origin_city: str | None = None
    destination: str | None = None
    origin_airport_code: str | None = None
    budget_try: float | None = None
    people_count: int | None = None
    start_date: str | None = None
    end_date: str | None = None
    nature_weight: int | None = None
    food_weight: int | None = None
    history_weight: int | None = None
    nightlife_weight: int | None = None


def _kullanici(voyage_session):
    payload, email = _main().current_user(voyage_session)
    return int(payload["sub"]), email


ONAY_MESAJI = "Seyahatin oluşturuldu"


def _yetimleri_temizle(db, user_id: int) -> None:
    """Silinmiş seyahatlerden kalan mesajları siler.

    Eski veritabanı kuralı (ON DELETE SET NULL) yüzünden seyahat silinince
    mesajların trip_id'si boşalıyordu. Seyahati onaylayan "Seyahatin oluşturuldu"
    mesajı sadece seyahate bağlı olarak yazılır; trip_id'si boş böyle bir mesaj
    varsa o sohbetin seyahati silinmiş demektir. Bu mesaj ve ondan önceki
    trip_id'si boş bütün mesajlar silinir; sonrasında başlamış açık sohbet kalır.
    """
    db.execute(
        """
        DELETE FROM ai_messages m
        WHERE m.user_id = %s AND m.trip_id IS NULL
          AND EXISTS (
              SELECT 1 FROM ai_messages o
              WHERE o.user_id = m.user_id AND o.trip_id IS NULL
                AND o.role = 'assistant' AND o.content LIKE %s
                AND (o.created_at, o.id) >= (m.created_at, m.id)
          )
        """,
        (user_id, ONAY_MESAJI + "%"),
    )


def _acik_mesajlar(db, user_id: int):
    return db.execute(
        """
        SELECT id, role, content, extracted_json, created_at
        FROM ai_messages
        WHERE user_id = %s AND trip_id IS NULL
        ORDER BY created_at, id
        """,
        (user_id,),
    ).fetchall()


def _sehirler(db) -> list[str]:
    """Gidilecek şehir olarak tanınan adlar (B'nin sehirler tablosu)."""
    return [r["ad"] for r in db.execute("SELECT ad FROM sehirler").fetchall()]


def _gecmis(db, user_id: int, limit: int = 80):
    """Ekranda gösterilecek son mesajlar: seyahate dönüşmüş eski sohbetler dahil."""
    satirlar = db.execute(
        """
        SELECT id, trip_id, role, content, created_at
        FROM ai_messages
        WHERE user_id = %s
        ORDER BY created_at DESC, id DESC
        LIMIT %s
        """,
        (user_id, limit),
    ).fetchall()
    return list(reversed(satirlar))


def _durum(mesajlar) -> dict:
    """Son asistan mesajındaki anlaşılan bilgiler."""
    for m in reversed(mesajlar):
        if m["role"] == "assistant" and m["extracted_json"]:
            return json.loads(m["extracted_json"])
    return {"bilgi": {}, "eksik": [], "hatalar": [], "hazir": False, "kaynak": None}


def _cikti(m) -> dict:
    return {"id": m["id"], "role": m["role"], "content": m["content"],
            "trip_id": m.get("trip_id"), "created_at": m["created_at"].isoformat()}


@router.get("/chat")
def sohbeti_getir(voyage_session: str | None = Cookie(default=None)):
    user_id, _ = _kullanici(voyage_session)
    with _main().conn() as db:
        _yetimleri_temizle(db, user_id)
        acik = _acik_mesajlar(db, user_id)
        gecmis = _gecmis(db, user_id)
    return {"messages": [_cikti(m) for m in gecmis], "durum": _durum(acik)}


@router.post("/chat")
def mesaj_gonder(
    data: MesajGirdisi,
    request: Request,
    voyage_session: str | None = Cookie(default=None),
):
    user_id, email = _kullanici(voyage_session)
    # LLM çağrısı maliyetli olabilir: dakikada en çok 20 mesaj.
    _main().enforce_rate_limit(request, "ai_chat", email, ip_limit=40, account_limit=20)

    bugun = date.today()
    with _main().conn() as db:
        _yetimleri_temizle(db, user_id)
        kullanici_mesaji = db.execute(
            """INSERT INTO ai_messages (user_id, role, content)
               VALUES (%s, 'user', %s) RETURNING id, trip_id, role, content, created_at""",
            (user_id, data.message.strip()),
        ).fetchone()

        gecmis = [m["content"] for m in _acik_mesajlar(db, user_id) if m["role"] == "user"]
        sehirler = _sehirler(db)
        bilgi, kaynak = cikar(gecmis, bugun, sehirler)
        temiz, eksik, hatalar = dogrula(bilgi, bugun, sehirler)
        durum = {
            "bilgi": {a: temiz.get(a) for a in ALANLAR},
            "eksik": eksik,
            "hatalar": hatalar,
            "hazir": not eksik and not hatalar,
            "kaynak": kaynak,
        }
        cevap = yanit_uret(eksik, hatalar)
        if temiz.get("varis_notu"):
            cevap = temiz["varis_notu"] + " " + cevap
        asistan_mesaji = db.execute(
            """INSERT INTO ai_messages (user_id, role, content, extracted_json)
               VALUES (%s, 'assistant', %s, %s) RETURNING id, trip_id, role, content, created_at""",
            (user_id, cevap, json.dumps(durum, ensure_ascii=False)),
        ).fetchone()

    return {"messages": [_cikti(kullanici_mesaji), _cikti(asistan_mesaji)], "durum": durum}


@router.delete("/chat")
def sohbeti_sil(voyage_session: str | None = Cookie(default=None)):
    user_id, _ = _kullanici(voyage_session)
    with _main().conn() as db:
        db.execute("DELETE FROM ai_messages WHERE user_id = %s AND trip_id IS NULL", (user_id,))
    return {"message": "Yeni sohbet başlatıldı."}


@router.post("/onayla", status_code=201)
def onayla(data: OnayGirdisi, voyage_session: str | None = Cookie(default=None)):
    """Kullanıcı kartı onaylayınca seyahati oluşturur."""
    main = _main()
    user_id, _ = _kullanici(voyage_session)

    with main.conn() as db:
        sehirler = _sehirler(db)
    temiz, eksik, hatalar = dogrula(data.model_dump(), date.today(), sehirler)
    if eksik or hatalar:
        raise HTTPException(422, yanit_uret(eksik, hatalar))
    if temiz.get("varis_notu"):
        raise HTTPException(422, temiz["varis_notu"] + " Şehir alanını boş bırakabilirsin.")

    with main.conn() as db:
        kullanici_metni = " ".join(
            m["content"] for m in _acik_mesajlar(db, user_id) if m["role"] == "user"
        )[:2000] or None

    try:
        seyahat_girdisi = main.TripCreate(
            title=baslik_uret(temiz),
            # Boşsa şehir sonra öneri ekranından seçilir
            destination=temiz.get("destination"),
            user_text=kullanici_metni,
            start_date=temiz["start_date"],
            end_date=temiz["end_date"],
            origin_city=temiz["origin_city"],
            origin_airport_code=temiz["origin_airport_code"],
            budget_try=temiz["budget_try"],
            people_count=temiz["people_count"],
            nature_weight=temiz["nature_weight"],
            food_weight=temiz["food_weight"],
            history_weight=temiz["history_weight"],
            nightlife_weight=temiz["nightlife_weight"],
        )
    except ValidationError as hata:
        raise HTTPException(422, hata.errors()[0].get("msg", "Bilgiler geçersiz."))

    # A'nın POST /trips kodu: seyahat + trip_members (sahip) + trip_preferences
    seyahat = main.create_trip(seyahat_girdisi, voyage_session)

    with main.conn() as db:
        db.execute(
            "UPDATE ai_messages SET trip_id = %s WHERE user_id = %s AND trip_id IS NULL",
            (seyahat["id"], user_id),
        )
        db.execute(
            """INSERT INTO ai_messages (user_id, trip_id, role, content)
               VALUES (%s, %s, 'assistant', %s)""",
            (user_id, seyahat["id"],
             f"{ONAY_MESAJI}: {seyahat['title']}. "
             + ("Uçuş ve otel aramaya geçebilirsin." if seyahat.get("destination")
                else "Şimdi sana uygun şehirleri seçebilirsin.")),
        )

    return {"trip": seyahat}
