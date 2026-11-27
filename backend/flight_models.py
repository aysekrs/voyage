
from sqlalchemy import (
    Column, BigInteger, Integer, String,
    Numeric, DateTime, ForeignKey,
    CheckConstraint
)
from database import Base


class Flight(Base):
    __tablename__ = "flights"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    trip_id = Column(
        BigInteger,
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False
    )

    destination_id = Column(
        Integer,
        ForeignKey("sehirler.sehir_id"),
        nullable=False
    )

    direction = Column(String(10), nullable=False)
    airline = Column(String(150))
    from_airport = Column(String(10))
    to_airport = Column(String(10))
    departure_time = Column(DateTime(timezone=True))
    arrival_time = Column(DateTime(timezone=True))
    price_per_person = Column(Numeric(12, 2))
    currency = Column(String(3))
    data_source = Column(String(20))

    __table_args__ = (
        CheckConstraint(
            "direction IN ('outbound', 'return')",
            name="flights_direction_check"
        ),
    )


class Accommodation(Base):
    __tablename__ = "accommodations"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    trip_id = Column(
        BigInteger,
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False
    )

    destination_id = Column(
        Integer,
        ForeignKey("sehirler.sehir_id"),
        nullable=False
    )

    hotel_name = Column(String(200), nullable=False)
    stars = Column(Integer)
    nightly_price = Column(Numeric(12, 2))
    currency = Column(String(3))
    data_source = Column(String(20))
