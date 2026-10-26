
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    ForeignKey
)

from sqlalchemy.orm import relationship

from database import Base


# ŞEHİRLER TABLOSU
class Sehir(Base):

    __tablename__ = "sehirler"

    sehir_id = Column(
        Integer,
        primary_key=True
    )

    ad = Column(
        String(100),
        nullable=False
    )

    ulke = Column(
        String(100),
        nullable=False
    )

    havalimani_kodu = Column(
        String(10),
        nullable=True
    )

    para_birimi = Column(
        String(3),
        nullable=True
    )

    doga_puani = Column(Float, nullable=True)

    yemek_puani = Column(Float, nullable=True)

    tarih_puani = Column(Float, nullable=True)

    gece_hayati_puani = Column(Float, nullable=True)

    gunluk_yemek_maliyeti = Column(
        Float,
        nullable=True
    )

    # Şehir ile gezilecek yerler arasındaki ilişki
    yerler = relationship(
        "Yer",
        back_populates="sehir"
    )


# GEZİLECEK YERLER TABLOSU
class Yer(Base):

    __tablename__ = "yerler"

    yer_id = Column(
        Integer,
        primary_key=True
    )

    sehir_id = Column(
        Integer,
        ForeignKey("sehirler.sehir_id"),
        nullable=False
    )

    ad = Column(
        String(200),
        nullable=False
    )

    kategori = Column(
        String(100),
        nullable=True
    )

    enlem = Column(
        Float,
        nullable=True
    )

    boylam = Column(
        Float,
        nullable=True
    )

    ziyaret_suresi = Column(
        Integer,
        nullable=True
    )

    ortalama_ucret = Column(
        Float,
        nullable=True
    )

    # Gezilecek yerin bağlı olduğu şehir
    sehir = relationship(
        "Sehir",
        back_populates="yerler"
    )
