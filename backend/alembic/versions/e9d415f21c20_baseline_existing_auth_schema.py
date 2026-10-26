
"""Baseline existing VoyageAI authentication schema.

Revision ID: e9d415f21c20
Revises:
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e9d415f21c20"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Kullanıcılar
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "failed_logins",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("locked_until", sa.DateTime(timezone=True)),
        sa.Column("kvkk_onay", sa.Boolean()),
        sa.Column("kvkk_onay_tarihi", sa.DateTime(timezone=True)),
        sa.Column(
            "session_version",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.UniqueConstraint("email", name="users_email_key"),
    )

    # 2. Doğrulama bekleyen kayıtlar
    op.create_table(
        "pending_signups",
        sa.Column("email", sa.Text(), primary_key=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("otp_hash", sa.Text(), nullable=False),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("kvkk_onay", sa.Boolean()),
    )

    # 3. Şifre sıfırlama kodları
    op.create_table(
        "password_resets",
        sa.Column(
            "email",
            sa.Text(),
            sa.ForeignKey("users.email", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("otp_hash", sa.Text(), nullable=False),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # 4. İptal edilmiş JWT oturumları
    op.create_table(
        "revoked_sessions",
        sa.Column("jti", sa.Text(), primary_key=True),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
    )

    # 5. API hız sınırları
    op.create_table(
        "auth_rate_limits",
        sa.Column("rate_key", sa.Text(), primary_key=True),
        sa.Column(
            "hits",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "window_started",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )


def downgrade() -> None:
    # Bilerek kapalı: mevcut kullanıcı ve oturum
    # verilerinin yanlışlıkla silinmesini önler.
    raise RuntimeError(
        "Baseline migration geri alınamaz. "
        "Veritabanı tabloları otomatik silinmeyecek."
    )
