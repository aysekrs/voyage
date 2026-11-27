
"""add flights and accommodations tables

Revision ID: 3cb6e322fd3f
Revises: d550b3094bf9
"""

from alembic import op
import sqlalchemy as sa


revision = "3cb6e322fd3f"
down_revision = "d550b3094bf9"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "flights",
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
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("airline", sa.String(150)),
        sa.Column("from_airport", sa.String(10)),
        sa.Column("to_airport", sa.String(10)),
        sa.Column("departure_time", sa.DateTime(timezone=True)),
        sa.Column("arrival_time", sa.DateTime(timezone=True)),
        sa.Column("price_per_person", sa.Numeric(12, 2)),
        sa.Column("currency", sa.String(3)),
        sa.Column("data_source", sa.String(20)),
        sa.CheckConstraint(
            "direction IN ('outbound', 'return')",
            name="flights_direction_check",
        ),
    )

    op.create_table(
        "accommodations",
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
        sa.Column("hotel_name", sa.String(200), nullable=False),
        sa.Column("stars", sa.Integer()),
        sa.Column("nightly_price", sa.Numeric(12, 2)),
        sa.Column("currency", sa.String(3)),
        sa.Column("data_source", sa.String(20)),
    )


def downgrade():
    op.drop_table("accommodations")
    op.drop_table("flights")
