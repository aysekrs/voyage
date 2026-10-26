
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    ForeignKey
)

from sqlalchemy.orm import relationship
from database import Base


# Şehirler tablosu
class Destination(Base):

    __tablename__ = "destinations"

    id = Column(Integer, primary_key=True)

    name = Column(
        String(100),
        nullable=False,
        unique=True
    )

    country = Column(
        String(100),
        nullable=False
    )

    places = relationship(
        "Place",
        back_populates="destination"
    )


# Gezilecek yerler tablosu
class Place(Base):

    __tablename__ = "places"

    id = Column(Integer, primary_key=True)

    destination_id = Column(
        Integer,
        ForeignKey("destinations.id"),
        nullable=False
    )

    name = Column(String(200), nullable=False)

    category = Column(String(100), nullable=False)

    latitude = Column(Float, nullable=False)

    longitude = Column(Float, nullable=False)

    visit_duration = Column(Integer, nullable=False)

    average_price = Column(Float, nullable=False)

    destination = relationship(
        "Destination",
        back_populates="places"
    )
