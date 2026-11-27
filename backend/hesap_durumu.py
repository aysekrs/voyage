"""Yerel test: bir e-postanın hesap durumunu gösterir (DEV_MODE için).

Kullanım (backend klasöründe):
    python hesap_durumu.py ornek@mail.com            -> sadece durumu gösterir
    python hesap_durumu.py ornek@mail.com --onayla   -> doğrulanmamış kaydı hesaba çevirir
    python hesap_durumu.py ornek@mail.com --kilidi-ac -> hatalı giriş kilidini kaldırır

--onayla, e-posta kodu girilmeden hesabı açar. Bu yüzden sadece
.env içinde DEV_MODE=true olduğunda çalışır.
"""
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv(Path(__file__).resolve().parent / ".env")
url = os.getenv("DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://")
dev = os.getenv("DEV_MODE", "false").lower() == "true"

if len(sys.argv) < 2:
    raise SystemExit(__doc__)
email = sys.argv[1].strip().lower()
secenek = sys.argv[2] if len(sys.argv) > 2 else ""

with psycopg.connect(url, row_factory=dict_row) as db:
    kullanici = db.execute(
        "SELECT id, failed_logins, locked_until FROM users WHERE email=%s", (email,)
    ).fetchone()
    bekleyen = db.execute(
        "SELECT expires_at, attempts FROM pending_signups WHERE email=%s", (email,)
    ).fetchone()

    if kullanici:
        print(f"HESAP VAR (id={kullanici['id']}). Hatali giris sayisi: {kullanici['failed_logins']}")
        if kullanici["locked_until"]:
            print(f"KILITLI: {kullanici['locked_until']} saatine kadar.")
        print("Giris olmuyorsa sifre farklidir. Bu durumda 'Sifremi unuttum' ile sifirla.")
        if secenek == "--kilidi-ac":
            db.execute("UPDATE users SET failed_logins=0, locked_until=NULL WHERE id=%s", (kullanici["id"],))
            print("Kilit kaldirildi.")
    elif bekleyen:
        print("HESAP YOK: kayit yapilmis ama e-posta KODU ile dogrulanmamis.")
        print("Kod, A'nin backend penceresinde '[DEV ONLY] OTP for ...' satirinda yazar.")
        if secenek == "--onayla":
            if not dev:
                raise SystemExit("--onayla sadece DEV_MODE=true iken calisir.")
            db.execute(
                """INSERT INTO users (email, password_hash, kvkk_onay, kvkk_onay_tarihi)
                   SELECT email, password_hash, kvkk_onay, NOW()
                     FROM pending_signups WHERE email=%s""",
                (email,),
            )
            db.execute("DELETE FROM pending_signups WHERE email=%s", (email,))
            print("ONAYLANDI: artik kayit olurken girdigin sifreyle giris yapabilirsin.")
        else:
            print("Kodu bulamiyorsan:  python hesap_durumu.py", email, "--onayla")
    else:
        print("BU E-POSTAYLA HIC KAYIT YOK. Once 'Kayit ol' ile kayit olmalisin.")
