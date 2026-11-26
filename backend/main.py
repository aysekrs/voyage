from fastapi.middleware.cors import CORSMiddleware
"""VoyageAI Week 2: FastAPI auth MVP, separate from legacy Nuxt/Nitro handlers."""
from email.utils import formataddr
import os, secrets, hashlib, hmac, smtplib
from external_api import router as external_router
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal
from contextlib import asynccontextmanager
from jwt.exceptions import InvalidTokenError
import jwt, psycopg
from psycopg.rows import dict_row
from fastapi import FastAPI, HTTPException, Response, Request, Cookie
from pydantic import BaseModel, EmailStr, Field
from pwdlib import PasswordHash

DATABASE_URL = os.environ.get("DATABASE_URL", "")
JWT_SECRET = os.environ.get("JWT_SECRET", "")
DEV_MODE = os.environ.get("DEV_MODE", "false").lower() == "true"
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"
JWT_ISSUER = "voyageai-auth"
JWT_AUDIENCE = "voyageai-web"
passwords = PasswordHash.recommended()
DUMMY_HASH = passwords.hash("not-a-real-password")

def conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL must be configured")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

@asynccontextmanager
async def lifespan(app: FastAPI):
    if len(JWT_SECRET) < 32:
        raise RuntimeError("JWT_SECRET must have at least 32 characters")
    with conn() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS users (
            id BIGSERIAL PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            failed_logins INT NOT NULL DEFAULT 0,
            locked_until TIMESTAMPTZ
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS pending_signups (
            email TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            otp_hash TEXT NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            attempts INT NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS revoked_sessions (
            jti TEXT PRIMARY KEY, expires_at TIMESTAMPTZ NOT NULL
        )""")
        # Persistent per-client and per-account request limits.
        db.execute("""CREATE TABLE IF NOT EXISTS auth_rate_limits (
            rate_key TEXT PRIMARY KEY,
            hits INTEGER NOT NULL DEFAULT 0,
            window_started TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS password_resets (
            email TEXT PRIMARY KEY REFERENCES users(email) ON DELETE CASCADE,
            otp_hash TEXT NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )""")
        # Clean up expired denylist and stale rate-limit counters at startup.
        db.execute("DELETE FROM revoked_sessions WHERE expires_at <= NOW()")
        db.execute("DELETE FROM auth_rate_limits WHERE window_started < NOW() - INTERVAL '1 day'")
    yield

app = FastAPI(title="VoyageAI Auth", lifespan=lifespan)
app.include_router(external_router)

class Register(BaseModel):
    email: EmailStr
    sifre: str = Field(min_length=8, max_length=128)
    kvkk_onay: bool

class Verify(BaseModel):
    email: EmailStr
    kod: str = Field(pattern=r"^\d{6}$")

class Login(BaseModel):
    email: EmailStr
    sifre: str
    beniHatirla: bool = False
    
class HesapSil(BaseModel):
    sifre: str


def enforce_rate_limit(request: Request, action: str, email: str | None = None,
                       ip_limit: int = 30, account_limit: int = 10,
                       window_seconds: int = 60):
    """Database-backed fixed-window limits; do not trust X-Forwarded-For from clients."""
    ip = request.client.host if request.client else "unknown"
    identities = [(f"{action}:ip:{ip}", ip_limit)]
    if email:
        # Hash personal identifiers instead of storing raw email in the limiter table.
        email_key = hmac.new(JWT_SECRET.encode(), email.encode(), hashlib.sha256).hexdigest()
        identities.append((f"{action}:email:{email_key}", account_limit))
    blocked = False
    with conn() as db:
        for key, limit in identities:
            row = db.execute("""
                INSERT INTO auth_rate_limits (rate_key, hits, window_started)
                VALUES (%s, 1, NOW())
                ON CONFLICT (rate_key) DO UPDATE SET
                    hits = CASE WHEN auth_rate_limits.window_started <= NOW() - (%s * INTERVAL '1 second')
                                THEN 1 ELSE auth_rate_limits.hits + 1 END,
                    window_started = CASE WHEN auth_rate_limits.window_started <= NOW() - (%s * INTERVAL '1 second')
                                          THEN NOW() ELSE auth_rate_limits.window_started END
                RETURNING hits
            """, (key, window_seconds, window_seconds)).fetchone()
            if row["hits"] > limit:
                blocked = True
    # Raise after transaction commits; otherwise the limit counters roll back.
    if blocked:
        raise HTTPException(status_code=429, detail="Çok fazla istek. Biraz bekleyip tekrar deneyin.",
                            headers={"Retry-After": str(window_seconds)})


def digest(email, otp):
    return hmac.new(JWT_SECRET.encode(), f"{email}:{otp}".encode(), hashlib.sha256).hexdigest()


def send_otp(email, otp):
    if DEV_MODE:
        print(f"[DEV ONLY] OTP for {email}: {otp}", flush=True)
        return

    host, user, pw = (os.getenv(x, "") for x in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS"))
    if not (host and user and pw):
        raise HTTPException(503, "SMTP yapılandırılmamış.")

    msg = EmailMessage()
    msg["Subject"] = "VoyageAI doğrulama kodu"
    msg["From"] = formataddr(("VoyageAI", os.getenv("SMTP_FROM") or user))
    msg["To"] = email
    msg.set_content(f"Doğrulama kodunuz: {otp}\nKod 10 dakika geçerlidir.")

    with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=10) as smtp:
        smtp.starttls()
        smtp.login(user, pw)
        smtp.send_message(msg)


@app.get("/health")
def health():
    with conn() as db:
        db.execute("SELECT 1").fetchone()
    return {"ok": True}

class PasswordResetRequest(BaseModel):
    email: EmailStr


@app.post("/auth/password-reset/request")
def password_reset_request(data: PasswordResetRequest, request: Request):
    email = str(data.email).strip().lower()
    enforce_rate_limit(request, "reset_request", email, ip_limit=12, account_limit=5)

    # Kullanıcı varlığını dışarıya açıklamıyoruz.
    success_message = {
        "message": "E-posta kayıtlıysa şifre sıfırlama kodu gönderilecektir."
    }

    with conn() as db:
        user = db.execute(
            "SELECT email FROM users WHERE email = %s",
            (email,)
        ).fetchone()

        if not user:
            return success_message

        # Enforce cooldown in the database, not just in the browser timer.
        existing = db.execute(
            "SELECT created_at FROM password_resets WHERE email=%s FOR UPDATE", (email,)
        ).fetchone()
        if existing and existing["created_at"] > datetime.now(timezone.utc) - timedelta(seconds=60):
            return success_message

        # Önceki kodu geçersiz kılacak yeni bir kod oluştur.
        otp = f"{secrets.randbelow(1000000):06d}"
        otp_hash = digest(email, otp)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        db.execute(
            """
            INSERT INTO password_resets
                (email, otp_hash, expires_at, attempts)
            VALUES (%s, %s, %s, 0)
            ON CONFLICT (email)
            DO UPDATE SET
                otp_hash = EXCLUDED.otp_hash,
                expires_at = EXCLUDED.expires_at,
                attempts = 0,
                created_at = NOW()
            """,
            (email, otp_hash, expires_at)
        )
        db.commit()

        
    try:
        send_otp(email, otp)
    except Exception as e:
        print(f"OTP gönderim hatası: {type(e).__name__}: {e}", flush=True)

        # Gönderilemeyen kodu kullanılabilir bırakma.
        with conn() as db:
            db.execute(
                "DELETE FROM password_resets WHERE email = %s AND otp_hash = %s",
                (email, otp_hash)
            )
            db.commit()

        raise HTTPException(
            status_code=503,
            detail="Şifre sıfırlama e-postası gönderilemedi."
        )

    return success_message



class PasswordResetConfirm(BaseModel):
    email: EmailStr
    kod: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    yeniSifre: str = Field(min_length=8, max_length=128)


@app.post("/auth/password-reset/confirm")
def password_reset_confirm(data: PasswordResetConfirm, request: Request):
    email = str(data.email).strip().lower()
    enforce_rate_limit(request, "reset_confirm", email, ip_limit=30, account_limit=12)

    # Kayıt ekranındaki şifre kurallarıyla uyumlu.
    if not any(c.isupper() for c in data.yeniSifre) or not any(
        c.islower() for c in data.yeniSifre
    ):
        raise HTTPException(422, "Şifre büyük ve küçük harf içermeli.")

    with conn() as db:
        row = db.execute(
            """
            SELECT otp_hash, expires_at, attempts
            FROM password_resets
            WHERE email = %s
            FOR UPDATE
            """,
            (email,),
        ).fetchone()

        if (
            not row
            or row["expires_at"] <= datetime.now(timezone.utc)
            or row["attempts"] >= 5
        ):
            raise HTTPException(400, "Kod geçersiz veya süresi dolmuş.")

        if not hmac.compare_digest(row["otp_hash"], digest(email, data.kod)):
            db.execute(
                """
                UPDATE password_resets
                SET attempts = attempts + 1
                WHERE email = %s
                """,
                (email,),
            )
            db.commit()
            raise HTTPException(400, "Doğrulama kodu hatalı.")

        yeni_hash = passwords.hash(data.yeniSifre)

        db.execute(
            """
            UPDATE users
            SET password_hash = %s,
                failed_logins = 0,
                locked_until = NULL,
                session_version = session_version + 1
            WHERE email = %s
            """,
            (yeni_hash, email),
        )

        db.execute(
            "DELETE FROM password_resets WHERE email = %s",
            (email,),
        )

    return {"message": "Şifreniz başarıyla güncellendi. Yeniden giriş yapabilirsiniz."}



@app.post("/auth/register")
def register(data: Register, request: Request):
    enforce_rate_limit(request, "register", str(data.email).lower(), ip_limit=12, account_limit=5)
    if not data.kvkk_onay:
        raise HTTPException(422, "KVKK onayı gerekli.")
    if not any(c.isupper() for c in data.sifre) or not any(c.islower() for c in data.sifre):
        raise HTTPException(422, "Şifre büyük ve küçük harf içermeli.")
    email = data.email.lower()
    with conn() as db:
        if db.execute("SELECT 1 FROM users WHERE email=%s", (email,)).fetchone():
            raise HTTPException(409, "Bu e-posta zaten kayıtlı.")

    otp = f"{secrets.randbelow(1000000):06d}"
    hashed = passwords.hash(data.sifre)
    # Send before inserting; if SMTP fails, do not leave a misleading pending record.
    send_otp(email, otp)

    with conn() as db:
        db.execute(
            """
            INSERT INTO pending_signups
                (email, password_hash, otp_hash, expires_at, kvkk_onay)
            VALUES
                (%s, %s, %s, NOW() + INTERVAL '10 minutes', %s)
            ON CONFLICT (email) DO UPDATE SET
                password_hash = EXCLUDED.password_hash,
                otp_hash = EXCLUDED.otp_hash,
                expires_at = EXCLUDED.expires_at,
                kvkk_onay = EXCLUDED.kvkk_onay,
                attempts = 0
            """,
            (email, hashed, digest(email, otp), data.kvkk_onay),
        )

    return {"message": "Doğrulama kodu gönderildi."}

@app.post("/auth/verify")
def verify(data: Verify, request: Request):
    email = data.email.lower()
    enforce_rate_limit(request, "verify", email, ip_limit=30, account_limit=12)
    with conn() as db:
        row = db.execute("SELECT * FROM pending_signups WHERE email=%s FOR UPDATE", (email,)).fetchone()
        if not row or row["expires_at"] < datetime.now(timezone.utc) or row["attempts"] >= 5:
            raise HTTPException(400, "Kod geçersiz veya süresi dolmuş.")
        if not hmac.compare_digest(row["otp_hash"], digest(email, data.kod)):
            db.execute("UPDATE pending_signups SET attempts=attempts+1 WHERE email=%s", (email,))
            db.commit()
            raise HTTPException(400, "Doğrulama kodu hatalı.")
        if db.execute("SELECT 1 FROM users WHERE email=%s", (email,)).fetchone():
            raise HTTPException(409, "Hesap zaten mevcut.")

        db.execute(
            """
            INSERT INTO users
                (email, password_hash, kvkk_onay, kvkk_onay_tarihi)
            VALUES
                (%s, %s, %s, NOW())
            """,
            (email, row["password_hash"], row["kvkk_onay"]),
        )
        db.execute("DELETE FROM pending_signups WHERE email=%s", (email,))

    return {"message": "E-posta doğrulandı. Giriş yapabilirsiniz."}

@app.post("/auth/login")
def login(data: Login, response: Response, request: Request):
    email = data.email.lower()
    enforce_rate_limit(request, "login", email, ip_limit=30, account_limit=12)
    with conn() as db:
        row = db.execute("SELECT * FROM users WHERE email=%s FOR UPDATE", (email,)).fetchone()
        if row and row["locked_until"] and row["locked_until"] > datetime.now(timezone.utc):
            raise HTTPException(423, "Çok fazla hatalı giriş. Daha sonra tekrar deneyin.")
        valid = passwords.verify(data.sifre, row["password_hash"] if row else DUMMY_HASH)
        if not row or not valid:
            if row:
                db.execute("""UPDATE users SET failed_logins=failed_logins+1,
                              locked_until=CASE WHEN failed_logins+1>=5 THEN NOW()+INTERVAL '15 minutes'
                              ELSE NULL END WHERE id=%s""", (row["id"],))
            db.commit()
            raise HTTPException(401, "E-posta veya şifre hatalı.")
        db.execute("UPDATE users SET failed_logins=0, locked_until=NULL WHERE id=%s", (row["id"],))
    lifetime = 86400

    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(row["id"]),
            "jti": secrets.token_urlsafe(24),
            "sv": row["session_version"],
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(seconds=lifetime),
        },
        JWT_SECRET,
        algorithm="HS256",
    )

    response.set_cookie(
        "voyage_session",
        token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=lifetime,
        path="/",
    )

    return {"kullanici": email}




def decode_session(token: str):
    try:
        payload = jwt.decode(
            token, JWT_SECRET, algorithms=["HS256"],
            issuer=JWT_ISSUER, audience=JWT_AUDIENCE,
            options={"require": ["sub", "jti", "sv", "iss", "aud", "iat", "nbf", "exp"]},
        )
        if (not isinstance(payload.get("sub"), str)
                or not payload["sub"].isdigit()
                or not isinstance(payload.get("jti"), str)
                or not payload["jti"]
                or type(payload.get("sv")) is not int):
            raise InvalidTokenError("Invalid session claims")
        return payload
    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(401, "Oturum geçersiz.")


def current_user(token):
    if not token:
        raise HTTPException(401, "Oturum açılmamış.")
    payload = decode_session(token)
    with conn() as db:
        if db.execute("SELECT 1 FROM revoked_sessions WHERE jti=%s", (payload["jti"],)).fetchone():
            raise HTTPException(401, "Oturum sonlandırılmış.")
        
        row = db.execute(
            "SELECT email, session_version FROM users WHERE id=%s",
            (int(payload["sub"]),)
        ).fetchone()

        if not row:
            raise HTTPException(401, "Kullanıcı bulunamadı.")

        if payload.get("sv") != row["session_version"]:
            raise HTTPException(401, "Oturum geçersiz. Lütfen yeniden giriş yapın.")

    return payload, row["email"]


@app.delete("/auth/account")
def delete_account(
    data: HesapSil,
    response: Response,
    voyage_session: str | None = Cookie(default=None)
):
    payload, email = current_user(voyage_session)
    user_id = int(payload["sub"])

    with conn() as db:
        row = db.execute(
            "SELECT password_hash FROM users WHERE id=%s FOR UPDATE",
            (user_id,)
        ).fetchone()

        if not row:
            raise HTTPException(401, "Kullanıcı bulunamadı.")

        if not passwords.verify(data.sifre, row["password_hash"]):
            raise HTTPException(400, "Mevcut şifreniz hatalı.")

        db.execute(
            "DELETE FROM users WHERE id=%s",
            (user_id,)
        )

    response.delete_cookie("voyage_session", path="/")

    return {
        "success": True,
        "message": "Hesabınız silindi."
    }


@app.get("/auth/me")
def me(voyage_session: str | None = Cookie(default=None)):
    payload, email = current_user(voyage_session)

    with conn() as db:
        row = db.execute(
            """
            SELECT email, created_at, kvkk_onay, kvkk_onay_tarihi
            FROM users
            WHERE id = %s
            """,
            (int(payload["sub"]),)
        ).fetchone()

    if not row:
        raise HTTPException(404, "Kullanıcı bulunamadı.")

    return {
        "kullanici": row["email"],
        "email": row["email"],
        "olusturulma": row["created_at"].isoformat(),
        "kvkkOnay": row["kvkk_onay"],
        "kvkkOnayTarihi": (
            row["kvkk_onay_tarihi"].isoformat()
            if row["kvkk_onay_tarihi"]
            else None
        )
    }



@app.post("/auth/logout")
def logout(response: Response, voyage_session: str | None = Cookie(default=None)):
    if voyage_session:
        try:
            payload = decode_session(voyage_session)
            with conn() as db:
                db.execute("INSERT INTO revoked_sessions(jti,expires_at) VALUES(%s,to_timestamp(%s)) ON CONFLICT DO NOTHING",
                           (payload["jti"], payload["exp"]))
        except HTTPException:
            pass
    response.delete_cookie("voyage_session", path="/")
    return {"message": "Çıkış yapıldı."}

class Resend(BaseModel):
    email: EmailStr

@app.post("/auth/resend")
def resend(data: Resend, request: Request):
    email = data.email.lower()
    enforce_rate_limit(request, "resend", email, ip_limit=12, account_limit=5)
    with conn() as db:
        row = db.execute("SELECT created_at, expires_at FROM pending_signups WHERE email=%s", (email,)).fetchone()
        if not row:
            raise HTTPException(400, "Önce kayıt formunu doldurun.")
        # A simple rate limit; production requires a dedicated resend timestamp.
        if row["expires_at"] > datetime.now(timezone.utc) + timedelta(minutes=9):
            raise HTTPException(429, "Yeni kod istemeden önce biraz bekleyin.")
    otp = f"{secrets.randbelow(1000000):06d}"
    send_otp(email, otp)
    with conn() as db:
        db.execute("""UPDATE pending_signups SET otp_hash=%s, expires_at=NOW()+INTERVAL '10 minutes',
                      attempts=0 WHERE email=%s""", (digest(email, otp), email))
    return {"message": "Yeni doğrulama kodu gönderildi."}


# VoyageAI ?ehir ve seyahat API'leri
from city_routes import router as city_router
app.include_router(city_router)


# Frontend CORS izni
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3005", "http://127.0.0.1:3005"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
from datetime import date
from pydantic import BaseModel, Field, model_validator


class TripCreate(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    # Boş bırakılabilir: AI asistanı seyahati şehir seçmeden oluşturur,
    # şehir 5. haftadaki öneri ekranından seçilir.
    destination: str | None = Field(default=None, max_length=150)
    # Kullanıcının AI'a yazdığı cümle (varsa)
    user_text: str | None = Field(default=None, max_length=2000)
    start_date: date
    end_date: date

    origin_city: str = Field(min_length=1, max_length=150)
    origin_airport_code: str = Field(min_length=1, max_length=10)
    budget_try: float = Field(gt=0)
    people_count: int = Field(gt=0)

    nature_weight: int = Field(ge=0, le=100)
    food_weight: int = Field(ge=0, le=100)
    history_weight: int = Field(ge=0, le=100)
    nightlife_weight: int = Field(ge=0, le=100)

    @model_validator(mode="after")
    def check_trip(self):
        if self.end_date <= self.start_date:
            raise ValueError(
                "Bitiş tarihi başlangıç tarihinden sonra olmalıdır."
            )

        if not self.origin_city.strip():
            raise ValueError("Çıkış şehri boş olamaz.")

        if not self.origin_airport_code.strip():
            raise ValueError("Havalimanı kodu boş olamaz.")

        total = (
            self.nature_weight
            + self.food_weight
            + self.history_weight
            + self.nightlife_weight
        )

        if total != 100:
            raise ValueError(
                "Dört ilgi ağırlığının toplamı 100 olmalıdır."
            )

        return self


def find_destination_id(db, destination_name: str) -> int:
    """Seçilen şehri veritabanından bul; şehir ID'sini sabit kodlama."""
    name = destination_name.strip()
    row = db.execute(
        "SELECT sehir_id FROM sehirler WHERE LOWER(TRIM(ad)) = LOWER(%s) ORDER BY sehir_id LIMIT 1",
        (name,),
    ).fetchone()
    if not row:
        raise HTTPException(422, f"'{name}' şehri şehirler veritabanında bulunamadı.")
    return row["sehir_id"]


@app.post("/trips", status_code=201)
def create_trip(
    data: TripCreate,
    voyage_session: str | None = Cookie(default=None)
):
    payload, _ = current_user(voyage_session)
    user_id = int(payload["sub"])

    with conn() as db:
        with db.transaction():
            destination = (data.destination or "").strip() or None
            destination_id = (
                find_destination_id(db, destination) if destination else None
            )
            trip = db.execute(
                """
                INSERT INTO trips (
                    user_id, title, destination,
                    start_date, end_date,
                    origin_city, origin_airport_code,
                    budget_try, people_count, selected_destination_id,
                    user_text
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    user_id,
                    data.title.strip(),
                    destination,
                    data.start_date,
                    data.end_date,
                    data.origin_city.strip(),
                    data.origin_airport_code.strip().upper(),
                    data.budget_try,
                    data.people_count,
                    destination_id,
                    data.user_text,
                ),
            ).fetchone()

            db.execute(
                """
                INSERT INTO trip_members (trip_id, user_id, role)
                VALUES (%s, %s, 'owner')
                """,
                (trip["id"], user_id),
            )

            db.execute(
                """
                INSERT INTO trip_preferences (
                    trip_id,
                    nature_weight,
                    food_weight,
                    history_weight,
                    nightlife_weight
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    trip["id"],
                    data.nature_weight,
                    data.food_weight,
                    data.history_weight,
                    data.nightlife_weight,
                ),
            )

    return trip


@app.get("/trips")
def list_trips(
    voyage_session: str | None = Cookie(default=None)
):
    payload, _ = current_user(voyage_session)
    user_id = int(payload["sub"])

    with conn() as db:
        trips = db.execute(
            """
            SELECT
                t.id,
                t.title,
                t.destination,
                t.start_date,
                t.end_date,
                t.created_at,
                tm.role
            FROM trips t
            JOIN trip_members tm ON tm.trip_id = t.id
            WHERE tm.user_id = %s
            ORDER BY t.created_at DESC, t.id DESC
            """,
            (user_id,)
        ).fetchall()

    return {"trips": trips}

from fastapi import Path

@app.get("/trips/{trip_id}")
def get_trip(
    trip_id: int = Path(gt=0),
    voyage_session: str | None = Cookie(default=None)
):
    payload, _ = current_user(voyage_session)

    with conn() as db:
        trip = db.execute("""
            
SELECT
    t.*,
    tm.role,
    tp.nature_weight,
    tp.food_weight,
    tp.history_weight,
    tp.nightlife_weight
FROM trips t
JOIN trip_members tm ON tm.trip_id = t.id
LEFT JOIN trip_preferences tp ON tp.trip_id = t.id
WHERE t.id = %s AND tm.user_id = %s

        """, (trip_id, int(payload["sub"]))).fetchone()

    if not trip:
        raise HTTPException(404, "Seyahat bulunamadı.")

    return trip



@app.put("/trips/{trip_id}")
def update_trip(
    trip_id: int,
    data: TripCreate,
    voyage_session: str | None = Cookie(default=None)
):
    payload, _ = current_user(voyage_session)
    user_id = int(payload["sub"])

    with conn() as db:
        with db.transaction():
            destination = (data.destination or "").strip() or None
            destination_id = (
                find_destination_id(db, destination) if destination else None
            )
            trip = db.execute(
                """
                UPDATE trips
                SET title = %s,
                    destination = %s,
                    start_date = %s,
                    end_date = %s,
                    origin_city = %s,
                    origin_airport_code = %s,
                    budget_try = %s,
                    people_count = %s,
                    selected_destination_id = %s,
                    updated_at = NOW()
                WHERE id = %s
                  AND EXISTS (
                      SELECT 1 FROM trip_members
                      WHERE trip_id = trips.id
                        AND user_id = %s
                        AND role = 'owner'
                  )
                RETURNING *
                """,
                (
                    data.title.strip(),
                    destination,
                    data.start_date,
                    data.end_date,
                    data.origin_city.strip(),
                    data.origin_airport_code.strip().upper(),
                    data.budget_try,
                    data.people_count,
                    destination_id,
                    trip_id,
                    user_id,
                ),
            ).fetchone()

            if not trip:
                raise HTTPException(
                    status_code=404,
                    detail="Seyahat bulunamadı veya yetkiniz yok."
                )

            db.execute(
                """
                INSERT INTO trip_preferences (
                    trip_id,
                    nature_weight,
                    food_weight,
                    history_weight,
                    nightlife_weight
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (trip_id)
                DO UPDATE SET
                    nature_weight = EXCLUDED.nature_weight,
                    food_weight = EXCLUDED.food_weight,
                    history_weight = EXCLUDED.history_weight,
                    nightlife_weight = EXCLUDED.nightlife_weight,
                    updated_at = NOW()
                """,
                (
                    trip_id,
                    data.nature_weight,
                    data.food_weight,
                    data.history_weight,
                    data.nightlife_weight,
                ),
            )

    return trip



@app.delete("/trips/{trip_id}")
def delete_trip(
    trip_id: int,
    voyage_session: str | None = Cookie(default=None)
):
    payload, _ = current_user(voyage_session)
    user_id = int(payload["sub"])

    with conn() as db:
        deleted = db.execute("""
            DELETE FROM trips
            WHERE id = %s
              AND EXISTS (
                  SELECT 1 FROM trip_members
                  WHERE trip_id = trips.id
                    AND user_id = %s
                    AND role = 'owner'
              )
            RETURNING id
        """, (trip_id, user_id)).fetchone()

        if not deleted:
            raise HTTPException(404, "Seyahat bulunamadı veya yetkiniz yok.")

        db.commit()

    return {"ok": True, "deleted_trip_id": deleted["id"]}
from pydantic import BaseModel, Field


class PreferencesUpdate(BaseModel):
    nature_score: int = Field(ge=0, le=100)
    food_score: int = Field(ge=0, le=100)
    history_score: int = Field(ge=0, le=100)
    nightlife_score: int = Field(ge=0, le=100)


@app.get("/preferences")
def get_preferences(
    voyage_session: str | None = Cookie(default=None)
):
    payload, _ = current_user(voyage_session)
    user_id = int(payload["sub"])

    with conn() as db:
        row = db.execute(
            """
            SELECT nature_score, food_score,
                   history_score, nightlife_score, updated_at
            FROM preferences
            WHERE user_id = %s
            """,
            (user_id,)
        ).fetchone()

    if not row:
        return {
            "nature_score": 0,
            "food_score": 0,
            "history_score": 0,
            "nightlife_score": 0,
            "updated_at": None
        }

    return row


@app.put("/preferences")
def update_preferences(
    data: PreferencesUpdate,
    voyage_session: str | None = Cookie(default=None)
):
    payload, _ = current_user(voyage_session)
    user_id = int(payload["sub"])

    with conn() as db:
        row = db.execute(
            """
            INSERT INTO preferences (
                user_id, nature_score, food_score,
                history_score, nightlife_score
            )
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id)
            DO UPDATE SET
                nature_score = EXCLUDED.nature_score,
                food_score = EXCLUDED.food_score,
                history_score = EXCLUDED.history_score,
                nightlife_score = EXCLUDED.nightlife_score,
                updated_at = NOW()
            RETURNING nature_score, food_score,
                      history_score, nightlife_score, updated_at
            """,
            (
                user_id,
                data.nature_score,
                data.food_score,
                data.history_score,
                data.nightlife_score
            )
        ).fetchone()

        db.commit()

    return row

# 4. Hafta - Seyahate ucus secenegi kaydetme
class FlightSave(BaseModel):
    destination_id: int = Field(gt=0)
    direction: Literal["outbound", "return"]
    airline: str | None = Field(default=None, max_length=150)
    from_airport: str | None = Field(default=None, max_length=10)
    to_airport: str | None = Field(default=None, max_length=10)
    departure_time: datetime | None = None
    arrival_time: datetime | None = None
    price_per_person: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    data_source: Literal["real", "mock"]


@app.post("/trips/{trip_id}/flights", status_code=201)
def save_trip_flight(
    data: FlightSave,
    trip_id: int = Path(gt=0),
    voyage_session: str | None = Cookie(default=None)
):
    payload, _ = current_user(voyage_session)
    user_id = int(payload["sub"])

    with conn() as db:
        with db.transaction():
            authorized = db.execute(
                """
                SELECT 1 FROM trip_members
                WHERE trip_id = %s AND user_id = %s AND role = 'owner'
                """,
                (trip_id, user_id)
            ).fetchone()

            if not authorized:
                raise HTTPException(404, "Seyahat bulunamadı veya kayıt yetkiniz yok.")

            destination = db.execute(
                "SELECT 1 FROM sehirler WHERE sehir_id = %s",
                (data.destination_id,)
            ).fetchone()
            if not destination:
                raise HTTPException(422, "Seçilen şehir bulunamadı.")

            flight = db.execute(
                """
                INSERT INTO flights (
                    trip_id, destination_id, direction, airline,
                    from_airport, to_airport, departure_time, arrival_time,
                    price_per_person, currency, data_source
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    trip_id, data.destination_id, data.direction,
                    data.airline,
                    data.from_airport.upper() if data.from_airport else None,
                    data.to_airport.upper() if data.to_airport else None,
                    data.departure_time, data.arrival_time,
                    data.price_per_person,
                    data.currency.upper() if data.currency else None,
                    data.data_source
                )
            ).fetchone()

    return flight


# 4. Hafta - Seyahate otel secenegi kaydetme
class AccommodationSave(BaseModel):
    destination_id: int = Field(gt=0)
    hotel_name: str = Field(min_length=1, max_length=200)
    stars: int | None = Field(default=None, ge=0, le=5)
    nightly_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    currency: str | None = Field(default=None, pattern=r"^[A-Za-z]{3}$")
    data_source: Literal["real", "mock"]


@app.post("/trips/{trip_id}/accommodations", status_code=201)
def save_trip_accommodation(
    data: AccommodationSave,
    trip_id: int = Path(gt=0),
    voyage_session: str | None = Cookie(default=None)
):
    payload, _ = current_user(voyage_session)
    user_id = int(payload["sub"])
    hotel_name = data.hotel_name.strip()
    if not hotel_name:
        raise HTTPException(422, "Otel adı boş olamaz.")

    with conn() as db:
        with db.transaction():
            authorized = db.execute(
                """
                SELECT 1 FROM trip_members
                WHERE trip_id = %s AND user_id = %s AND role = 'owner'
                """,
                (trip_id, user_id)
            ).fetchone()

            if not authorized:
                raise HTTPException(404, "Seyahat bulunamadı veya kayıt yetkiniz yok.")

            destination = db.execute(
                "SELECT 1 FROM sehirler WHERE sehir_id = %s",
                (data.destination_id,)
            ).fetchone()
            if not destination:
                raise HTTPException(422, "Seçilen şehir bulunamadı.")

            accommodation = db.execute(
                """
                INSERT INTO accommodations (
                    trip_id, destination_id, hotel_name, stars,
                    nightly_price, currency, data_source
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    trip_id, data.destination_id, hotel_name, data.stars,
                    data.nightly_price,
                    data.currency.upper() if data.currency else None,
                    data.data_source
                )
            ).fetchone()

    return accommodation


# 5. Hafta - Şehir önerileri (maliyet + puan), bkz. trip_options.py
import trip_options  # noqa: E402

trip_options.register(app, conn, current_user)
