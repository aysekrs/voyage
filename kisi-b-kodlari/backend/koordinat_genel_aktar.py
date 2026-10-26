"""VoyageAI: elle doğrulanmış koordinatları güvenle içe aktar.

Önizleme: python koordinat_genel_aktar.py
Aktarma:  python koordinat_genel_aktar.py --apply

Önce koordinat_266_ileri_denetim.csv dosyasında harita_onayi=ONAYLANDI
ve onayli_enlem/onayli_boylam alanlarını doldurun. Aday koordinatları
otomatik onaylanmaz. Önizleme DB'ye yazmaz.
"""
import argparse
import csv
import math
from collections import Counter
from pathlib import Path

from sqlalchemy import select
from database import SessionLocal
from city_models import Sehir, Yer

DOSYA = Path(__file__).resolve().parent / "koordinat_266_ileri_denetim.csv"
ALANLAR = {"yer_id", "ulke", "sehir", "yer_adi", "harita_onayi", "onayli_enlem", "onayli_boylam"}


def normalize(s):
    return " ".join(str(s or "").casefold().split())


def sayi(s, lo, hi, label):
    try:
        n = float(str(s).strip())
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{label}: sayi degil: {s!r}") from exc
    if not math.isfinite(n) or not lo <= n <= hi:
        raise ValueError(f"{label}: gecersiz deger: {s!r}")
    return n


def oku():
    if not DOSYA.is_file():
        raise ValueError(f"CSV bulunamadi: {DOSYA}")
    with DOSYA.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        if not r.fieldnames or not ALANLAR.issubset(set(r.fieldnames)):
            raise ValueError(f"CSV sutunlari eksik: {sorted(ALANLAR - set(r.fieldnames or []))}")
        satirlar = list(r)
    if any(None in x for x in satirlar):
        raise ValueError("CSV'de fazla alan bulunan satir var; once duzeltin.")
    ids = [x["yer_id"].strip() for x in satirlar]
    if len(ids) != len(set(ids)):
        raise ValueError("CSV'de tekrar eden yer_id bulundu. Aktarim durduruldu.")
    if len(satirlar) != 266:
        raise ValueError(f"Beklenen 266 kayit yerine {len(satirlar)} bulundu; dosyayi kontrol et.")
    onayli = []
    durumlar = Counter()
    for x in satirlar:
        durum = normalize(x["harita_onayi"])
        durumlar[durum or "bos"] += 1
        if durum not in {"onaylandi", "bekliyor", "belirsiz", "yanlis", "reddedildi"}:
            raise ValueError(f"{x['yer_id']}: bilinmeyen harita_onayi: {x['harita_onayi']!r}")
        if durum != "onaylandi":
            if x["onayli_enlem"].strip() or x["onayli_boylam"].strip():
                raise ValueError(f"{x['yer_id']}: onay yok ama onayli koordinat girilmis.")
            continue
        lat = sayi(x["onayli_enlem"], -90, 90, "enlem")
        lon = sayi(x["onayli_boylam"], -180, 180, "boylam")
        onayli.append((x, lat, lon))
    return satirlar, onayli, durumlar


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true", help="Kontrolden sonra DB'ye kaydet")
    args = p.parse_args()
    db = None
    try:
        satirlar, onayli, durumlar = oku()
        print("Toplam satir:", len(satirlar))
        print("Harita kontrol durumlari:", dict(durumlar))
        print("Acikca ONAYLANDI olan:", len(onayli))
        if not onayli:
            print("Kaydedilebilir onayli koordinat yok. VERITABANI DEGISTIRILMEDI.")
            print("Dogruladigin satirlarda harita_onayi=ONAYLANDI ve")
            print("onayli_enlem / onayli_boylam doldurulunca tekrar calistir.")
            return

        db = SessionLocal()
        hazir = []
        for x, lat, lon in onayli:
            try:
                yer_id = int(x["yer_id"])
            except ValueError as exc:
                raise ValueError(f"Gecersiz yer_id: {x['yer_id']}") from exc
            sonuc = db.execute(
                select(Yer, Sehir).join(Sehir, Yer.sehir_id == Sehir.sehir_id)
                .where(Yer.yer_id == yer_id)
            ).one_or_none()
            if sonuc is None:
                raise ValueError(f"Veritabaninda bulunamadi: yer_id={yer_id}")
            yer, sehir = sonuc
            if (normalize(yer.ad) != normalize(x["yer_adi"]) or
                normalize(sehir.ad) != normalize(x["sehir"]) or
                normalize(sehir.ulke) != normalize(x["ulke"])):
                raise ValueError(f"Kimlik/ad/sehir/ulke uyusmuyor: yer_id={yer_id}")
            if yer.enlem is not None or yer.boylam is not None:
                raise ValueError(f"Koordinat zaten dolu: yer_id={yer_id}; ustune yazilmadi")
            hazir.append((yer, lat, lon))
            print(f"HAZIR  ID {yer_id}: {sehir.ad} / {yer.ad}: {lat}, {lon}")

        if not args.apply:
            print(f"ONIZLEME: {len(hazir)} kayit uygun. VERITABANI DEGISTIRILMEDI.")
            print("Onaylananlar dogruysa --apply ile tekrar calistir.")
            return
        if input(f"{len(hazir)} kayit kaydedilecek. Devam icin EVET yaz: ").strip() != "EVET":
            print("Iptal edildi.")
            return
        for yer, lat, lon in hazir:
            yer.enlem = lat
            yer.boylam = lon
        db.commit()
        print(f"Basarili: {len(hazir)} kayit guncellendi.")
    except (ValueError, OSError) as exc:
        if db:
            db.rollback()
        print("KONTROL HATASI:", exc)
        raise SystemExit(1)
    except Exception:
        if db:
            db.rollback()
        raise
    finally:
        if db:
            db.close()


if __name__ == "__main__":
    main()
