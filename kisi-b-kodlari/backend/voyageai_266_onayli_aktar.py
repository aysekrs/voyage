"""VoyageAI: import user-reviewed map POI positions into yerler.

Usage (from VoyageAI/backend):
 python voyageai_266_onayli_aktar.py

Requires database.py SessionLocal, the 266 user-checked CSV in the same folder,
and a PostgreSQL backup. Dry-run summary is printed before a single explicit EVET.
No changes to koordinat_adaylari: original candidate status/provenance preserved.
"""
from __future__ import annotations
import csv
import math
from collections import Counter
from datetime import datetime
from pathlib import Path
from sqlalchemy import text
from database import SessionLocal

BASE = Path(__file__).resolve().parent
CSV_FILE = BASE / "VoyageAI_266_Dogrulanmis_Kontrol_Duzeltilmis.csv"
REPORT_FILE = BASE / "VoyageAI_266_Aktarim_Sonucu.csv"
EXPECTED = {"yer_id", "ulke", "sehir", "gezilecek_yer", "aday_enlem", "aday_boylam", "yer_eslesmesi_onayi", "kontrol_sonucu"}


def normalize(s):
    # Turkish casing handled for common İ/i variation; otherwise preserve accents.
    return str(s or "").strip().replace("İ", "i").replace("I", "ı").casefold()


def parse_number(v):
    s = str(v or "").strip().replace(",", ".")
    return float(s)


def main():
    if not CSV_FILE.exists():
        raise SystemExit(f"CSV bulunamadi: {CSV_FILE}\nDosyayi backend klasorune kopyala.")
    with CSV_FILE.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        if not EXPECTED.issubset(reader.fieldnames or []):
            raise SystemExit("CSV basliklari beklenenden farkli: " + str(reader.fieldnames))
        rows = list(reader)
    if len(rows) != 266:
        raise SystemExit(f"Beklenen 266 satir yerine {len(rows)} satir var. Islem durduruldu.")
    ids = [r["yer_id"].strip() for r in rows]
    if len(set(ids)) != len(ids):
        raise SystemExit("CSV'de tekrar eden yer_id var. Islem durduruldu.")

    session = SessionLocal()
    results = []
    try:
        # A single SELECT; all validation and candidate updates happen in this transaction.
        dbrows = session.execute(text("""
            SELECT y.yer_id, y.ad AS yer_adi, s.ad AS sehir, s.ulke,
                   y.enlem AS ana_enlem, y.boylam AS ana_boylam,
                   k.enlem AS aday_enlem, k.boylam AS aday_boylam,
                   k.durum AS aday_durum, k.kaynak AS aday_kaynak
            FROM yerler y
            JOIN sehirler s ON s.sehir_id = y.sehir_id
            LEFT JOIN koordinat_adaylari k ON k.yer_id = y.yer_id
        """)).mappings().all()
        byid = {int(d["yer_id"]): d for d in dbrows}
        to_update = []
        for r in rows:
            vid = r["yer_id"].strip()
            state = ""
            try:
                pid = int(vid)
                d = byid.get(pid)
                if not d:
                    state = "ATLANDI_YER_YOK"
                elif normalize(r["yer_eslesmesi_onayi"]) != "onay":
                    state = "ATLANDI_ONAY_YOK"
                elif r["kontrol_sonucu"].strip() == "TEMSILI_KONUM_INCELE" or "temsil" in r.get("kaynak", "").lower():
                    state = "ATLANDI_TEMSILI_KONUM"
                elif normalize(d["yer_adi"]) != normalize(r["gezilecek_yer"]) or normalize(d["sehir"]) != normalize(r["sehir"]) or normalize(d["ulke"]) != normalize(r["ulke"]):
                    state = "ATLANDI_YER_SEHIR_ULKE_FARKLI"
                else:
                    lat, lon = parse_number(r["aday_enlem"]), parse_number(r["aday_boylam"])
                    if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
                        state = "ATLANDI_GECERSIZ_KOORDINAT"
                    elif d["aday_enlem"] is None or d["aday_boylam"] is None:
                        state = "ATLANDI_VERITABANINDA_ADAY_YOK"
                    elif abs(float(d["aday_enlem"]) - lat) > 0.000001 or abs(float(d["aday_boylam"]) - lon) > 0.000001:
                        state = "ATLANDI_ADAY_DEGISMIS"
                    elif (d["ana_enlem"] is None) != (d["ana_boylam"] is None):
                        state = "ATLANDI_EKSIK_ANA_KOORDINAT_PARCA"
                    elif d["ana_enlem"] is not None and d["ana_boylam"] is not None:
                        state = "ATLANDI_ANA_KOORDINAT_ZATEN_VAR"
                    else:
                        state = "AKTARILACAK"
                        to_update.append((pid, lat, lon))
            except (ValueError, TypeError, OverflowError):
                state = "ATLANDI_VERI_HATASI"
            results.append({"yer_id": vid, "ulke": r["ulke"], "sehir": r["sehir"], "gezilecek_yer": r["gezilecek_yer"], "sonuc": state})

        print("\n--- AKTARIM ON KONTROL ---")
        for category, count in sorted(Counter(x["sonuc"] for x in results).items()):
            print(f"{category}: {count}")
        print("\nBu aktarim yalnizca kullanicinin haritada onayladigi ve veritabaninda ayni kalan adaylari alir.")
        print("3 temsili konum haric tutulur. Mevcut ana koordinatlar degistirilmez.")
        print("koordinat_adaylari tablosu / durumlar degistirilmez; kaynak denetimi icin saklanir.")
        print("Bu islem profesyonel/harici bagimsiz dogrulama iddiasi tasimaz.")
        if not to_update:
            print("Aktarilacak yeni yer yok; veritabaninda degisiklik yapilmadi.")
            session.rollback()
        else:
            confirmation = input("\nYedegini aldiktan sonra gercek aktarim icin EVET yaz: ").strip()
            if confirmation != "EVET":
                print("Islem iptal edildi; veritabaninda degisiklik yok.")
                session.rollback()
            else:
                updated = 0
                for pid, lat, lon in to_update:
                    # Conditional UPDATE also protects against unexpected concurrent updates.
                    result = session.execute(text("""
                        UPDATE yerler y SET enlem = :lat, boylam = :lon
                        WHERE y.yer_id = :pid AND y.enlem IS NULL AND y.boylam IS NULL
                          AND EXISTS (SELECT 1 FROM koordinat_adaylari k
                              WHERE k.yer_id = y.yer_id
                                AND ABS(k.enlem - :lat) < 0.000001
                                AND ABS(k.boylam - :lon) < 0.000001)
                    """), {"pid": pid, "lat": lat, "lon": lon})
                    if result.rowcount != 1:
                        raise RuntimeError(f"Aktarim sirasinda yer_id {pid} degisti. Tum islem geri alindi.")
                    updated += 1
                session.commit()
                for result in results:
                    if result["sonuc"] == "AKTARILACAK":
                        result["sonuc"] = "AKTARILDI"
                print(f"\nBASARILI: {updated} yeni koordinat ana yerler tablosuna aktarildi.")

        with REPORT_FILE.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["yer_id", "ulke", "sehir", "gezilecek_yer", "sonuc"], delimiter=";")
            writer.writeheader()
            writer.writerows(results)
        print(f"Rapor: {REPORT_FILE}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
