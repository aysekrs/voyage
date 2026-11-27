"""week5 ai_messages (Kişi B: AI asistan sohbet kayıtları)

Revision ID: b7e2a4c91d05
Revises: a5c0f1d2e3b4
Create Date: 2026-11-26

Seyahat oluşmadan da sohbet başlayabildiği için trip_id boş olabilir.
Kullanıcı onay kartını onaylayınca o sohbetin mesajlarına trip_id yazılır.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7e2a4c91d05"
down_revision: Union[str, Sequence[str], None] = "a5c0f1d2e3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_messages",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "trip_id",
            sa.BigInteger(),
            sa.ForeignKey("trips.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("extracted_json", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="ai_messages_role_check"),
    )
    op.create_index("ix_ai_messages_user_trip", "ai_messages", ["user_id", "trip_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_messages_user_trip", table_name="ai_messages")
    op.drop_table("ai_messages")
