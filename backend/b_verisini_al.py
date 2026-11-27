"""B'nin şehir ve yer verisini (pg_dump dosyası) bu veritabanına aktarır.

B kendi veritabanından şu komutla bir dosya üretir:
    docker exec <container> pg_dump -U postgres -d voyageai_db --no-owner \\
        -t sehirler -t yerler -f /tmp/sehir_yer.sql

Kullanım (backend klasöründe):
    py b_verisini_al.py sehir_yer.sql             -> sadece önizleme, hiçbir şey değişmez
    py b_verisini_al.py sehir_yer.sql --uygula    -> aktarır (tek işlem; hata olursa hiçbir şey değişmez)

Ne yapar:
  1. Önce kontrol: aynı numaralı şehirlerin adları iki tarafta da aynı mı?
     Değilse DURUR (seyahatler şehirlere numarayla bağlı, yanlış şehre bağlanmasın).
  2. yerler tablosunda eksik sütunları ekler (B'nin tablosundaki gibi).
  3. Şehirleri ve yerleri numarasına göre ekler/günceller (B'nin verisi esas alınır).
  4. B'de olmayan yerlere dokunmaz, sadece sayısını raporlar.
  5. Numara sayaçlarını (sequence) en büyük numaraya ayarlar.

Dosya B'nin kişisel veritabanından geldiği için repoya EKLENMEZ.
"""
import argparse
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

SEHIR_SUTUNLARI = [
    "sehir_id", "ad", "ulke", "havalimani_kodu", "para_birimi",
    "doga_puani", "yemek_puani", "tarih_puani", "gece_hayati_puani",
    "gunluk_yemek_maliyeti",
]

YER_SUTUNLARI = [
    "yer_id", "sehir_id", "ad", "kategori", "enlem", "boylam",
    "ziyaret_suresi", "ortalama_ucret", "veri_durumu", "kaynak_aday_id",
    "resmi_kaynak", "fiyat_para_birimi", "fiyat_turu", "fiyat_kontrol_tarihi",
    "ziyaret_suresi_turu",
]

# yerler'de A'nın veritabanında olmayabilecek sütunlar
EK_YER_SUTUNLARI = {
    "veri_durumu": "text",
    "kaynak_aday_id": "bigint",
    "resmi_kaynak": "text",
    "fiyat_para_birimi": "text",
    "fiyat_turu": "text",
    "fiyat_kontrol_tarihi": "date",
    "ziyaret_suresi_turu": "text",
}


# ---------------------------------------------------------------
# pg_dump dosyasını okuma
# ---------------------------------------------------------------

def _copy_degeri(deger: str):
    if deger == r"\N":
        return None
    # COPY metin biçimindeki kaçış dizileri
    return (
        deger.replace(r"\t", "\t").replace(r"\n", "\n")
        .replace(r"\r", "\r").replace("\\\\", "\\")
    )


def copy_blogu_oku(metin: str, tablo: str, beklenen: list[str]) -> list[dict]:
    eslesme = re.search(
        rf"COPY public\.{tablo} \(([^)]*)\) FROM stdin;\n(.*?)\n\\\.",
        metin,
        re.S,
    )
    if not eslesme:
        sys.exit(f"HATA: dosyada '{tablo}' verisi bulunamadı.")
    sutunlar = [s.strip() for s in eslesme.group(1).split(",")]
    eksik = set(beklenen) - set(sutunlar)
    if eksik:
        sys.exit(f"HATA: '{tablo}' verisinde beklenen sütunlar yok: {sorted(eksik)}")
    satirlar = []
    for satir in eslesme.group(2).split("\n"):
        if not satir:
            continue
        degerler = [_copy_degeri(d) for d in satir.split("\t")]
        kayit = dict(zip(sutunlar, degerler))
        satirlar.append({s: kayit[s] for s in beklenen})
    return satirlar


# ---------------------------------------------------------------
# SQL
# ---------------------------------------------------------------

def _upsert_sql(tablo: str, sutunlar: list[str], anahtar: str) -> str:
    ad_listesi = ", ".join(sutunlar)
    yer_tutucular = ", ".join(["%s"] * len(sutunlar))
    guncelle = ", ".join(f"{s} = EXCLUDED.{s}" for s in sutunlar if s != anahtar)
    return (
        f"INSERT INTO {tablo} ({ad_listesi}) VALUES ({yer_tutucular}) "
        f"ON CONFLICT ({anahtar}) DO UPDATE SET {guncelle}"
    )


def onizleme(db, sehirler: list[dict], yerler: list[dict]) -> bool:
    """Ekrana özet basar. Aktarım güvenliyse True döner."""
    mevcut_sehir = {
        r[0]: r[1] for r in db.execute("SELECT sehir_id, ad FROM sehirler").fetchall()
    }
    mevcut_yer = {
        r[0]: (r[1], r[2])
        for r in db.execute("SELECT yer_id, sehir_id, ad FROM yerler").fetchall()
    }

    uyumsuz = [
        (int(s["sehir_id"]), mevcut_sehir[int(s["sehir_id"])], s["ad"])
        for s in sehirler
        if int(s["sehir_id"]) in mevcut_sehir and mevcut_sehir[int(s["sehir_id"])] != s["ad"]
    ]
    yeni_sehir = [s for s in sehirler if int(s["sehir_id"]) not in mevcut_sehir]

    b_yer_idleri = {int(y["yer_id"]) for y in yerler}
    yeni_yer = [y for y in yerler if int(y["yer_id"]) not in mevcut_yer]
    ad_degisen = [
        (int(y["yer_id"]), mevcut_yer[int(y["yer_id"])][1], y["ad"])
        for y in yerler
        if int(y["yer_id"]) in mevcut_yer and mevcut_yer[int(y["yer_id"])][1] != y["ad"]
    ]
    sadece_burada = sorted(set(mevcut_yer) - b_yer_idleri)

    tam = sum(1 for y in yerler if y["enlem"] and y["boylam"] and y["ziyaret_suresi"])
    ucretli = sum(1 for y in yerler if y["ortalama_ucret"] is not None)

    print("=== B'nin dosyası ===")
    print(f"  şehir: {len(sehirler)}   yer: {len(yerler)}")
    print(f"  koordinatı ve süresi dolu yer: {tam}   ücreti dolu yer: {ucretli}")
    print()
    print("=== Bu veritabanı ===")
    print(f"  şehir: {len(mevcut_sehir)}   yer: {len(mevcut_yer)}")
    print()
    print("=== Yapılacaklar ===")
    print(f"  güncellenecek şehir: {len(sehirler) - len(yeni_sehir)}   yeni şehir: {len(yeni_sehir)}")
    print(f"  güncellenecek yer:   {len(yerler) - len(yeni_yer)}   yeni yer: {len(yeni_yer)}")
    if ad_degisen:
        print(f"  adı değişecek yer: {len(ad_degisen)} (ilk 5: {ad_degisen[:5]})")
    if sadece_burada:
        print(f"  B'de olmayan, DOKUNULMAYACAK yer: {len(sadece_burada)} (numaralar: {sadece_burada[:10]})")

    if uyumsuz:
        print()
        print("!!! DURDU: aynı numaralı şehirlerin adları farklı.")
        print("    Seyahatler şehirlere numarayla bağlı olduğu için aktarım yapılmadı.")
        for sid, bu, b in uyumsuz[:20]:
            print(f"    şehir {sid}: burada '{bu}', B'de '{b}'")
        return False
    return True


def aktar(db, sehirler: list[dict], yerler: list[dict]) -> None:
    with db.transaction():
        for sutun, tip in EK_YER_SUTUNLARI.items():
            db.execute(f"ALTER TABLE yerler ADD COLUMN IF NOT EXISTS {sutun} {tip}")

        with db.cursor() as imlec:
            imlec.executemany(
                _upsert_sql("sehirler", SEHIR_SUTUNLARI, "sehir_id"),
                [[s[c] for c in SEHIR_SUTUNLARI] for s in sehirler],
            )
            imlec.executemany(
                _upsert_sql("yerler", YER_SUTUNLARI, "yer_id"),
                [[y[c] for c in YER_SUTUNLARI] for y in yerler],
            )

        for tablo, sutun in (("sehirler", "sehir_id"), ("yerler", "yer_id")):
            db.execute(
                f"""
                SELECT setval(
                    pg_get_serial_sequence('{tablo}', '{sutun}'),
                    (SELECT MAX({sutun}) FROM {tablo})
                )
                WHERE pg_get_serial_sequence('{tablo}', '{sutun}') IS NOT NULL
                """
            )


def main() -> None:
    ayristirici = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ayristirici.add_argument("dosya", help="B'nin pg_dump dosyası (ör. sehir_yer.sql)")
    ayristirici.add_argument("--uygula", action="store_true", help="aktarımı gerçekten yap")
    secenek = ayristirici.parse_args()

    metin = Path(secenek.dosya).read_text(encoding="utf-8")
    sehirler = copy_blogu_oku(metin, "sehirler", SEHIR_SUTUNLARI)
    yerler = copy_blogu_oku(metin, "yerler", YER_SUTUNLARI)

    import psycopg  # yalnızca veritabanına bağlanırken gerekli

    load_dotenv(Path(__file__).resolve().parent / ".env")
    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")

    with psycopg.connect(url) as db:
        guvenli = onizleme(db, sehirler, yerler)
        if not guvenli:
            sys.exit(1)
        if not secenek.uygula:
            print()
            print("Bu sadece önizlemeydi; hiçbir şey değişmedi.")
            print("Aktarmak için:  py b_verisini_al.py", secenek.dosya, "--uygula")
            return
        aktar(db, sehirler, yerler)

    print()
    print("Aktarım tamam. Kontrol için:  py veri_kontrol.py")


if __name__ == "__main__":
    main()
