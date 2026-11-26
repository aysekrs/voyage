"""VoyageAI Week 2: FastAPI auth MVP, separate from legacy Nuxt/Nitro handlers."""
from email.utils import formataddr
import os, secrets, hashlib, hmac, smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone
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
