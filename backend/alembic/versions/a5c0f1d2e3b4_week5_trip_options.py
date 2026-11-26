"""week5 trip_options

Revision ID: a5c0f1d2e3b4
Revises: 3cb6e322fd3f
Create Date: 2026-11-26

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a5c0f1d2e3b4"
down_revision: Union[str, Sequence[str], None] = "3cb6e322fd3f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trip_options",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "trip_id",
            sa.BigInteger(),
            sa.ForeignKey("trips.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "destination_id",
            sa.Integer(),
            sa.ForeignKey("sehirler.sehir_id"),
            nullable=False,
        ),
        sa.Column(
            "outbound_flight_id",
            sa.BigInteger(),
            sa.ForeignKey("flights.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "return_flight_id",
            sa.BigInteger(),
            sa.ForeignKey("flights.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "accommodation_id",
            sa.BigInteger(),
            sa.ForeignKey("accommodations.id", ondelete="SET NULL"),
        ),
        sa.Column("flight_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("accommodation_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("food_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("activity_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("local_transport_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("remaining_budget", sa.Numeric(12, 2), nullable=False),
        sa.Column("preference_score", sa.Numeric(5, 1), nullable=False),
        sa.Column("budget_fit_score", sa.Numeric(5, 1), nullable=False),
        sa.Column("overall_score", sa.Numeric(5, 1), nullable=False),
        sa.Column("ai_explanation", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "trip_id", "destination_id", name="trip_options_trip_destination_key"
        ),
    )
    op.create_index("ix_trip_options_trip_id", "trip_options", ["trip_id"])

    # AI asistanı seyahati şehir seçmeden oluşturabilsin diye
    # trips.destination artık boş olabilir.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'trips' AND column_name = 'destination'
            ) THEN
                ALTER TABLE trips ALTER COLUMN destination DROP NOT NULL;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.drop_index("ix_trip_options_trip_id", table_name="trip_options")
    op.drop_table("trip_options")
