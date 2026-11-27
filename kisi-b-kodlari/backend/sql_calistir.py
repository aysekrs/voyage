"""Bir .sql dosyasını .env'deki DATABASE_URL veritabanında çalıştırır.

Kullanım:
    python sql_calistir.py sql/hafta4_itineraries.sql

psql kurmaya gerek kalmasın diye yazıldı. Dosyadaki SELECT'lerin
sonuçlarını ekrana tablo gibi basar. Bir hata olursa hiçbir şey kaydedilmez.
"""
import sys
from pathlib import Path

from database import engine


def sql_ifadelerine_bol(metin: str) -> list[str]:
    """Noktalı virgülle biten ifadeleri ayırır; yorum satırlarını ve
    tırnak içindeki noktalı virgülleri dikkate alır."""
    ifadeler, parca, tirnakta = [], [], False
    for satir in metin.splitlines():
        if not tirnakta and satir.strip().startswith("--"):
            continue
        for karakter in satir:
            if karakter == "'":
                tirnakta = not tirnakta
            if karakter == ";" and not tirnakta:
                ifade = "".join(parca).strip()
                if ifade:
                    ifadeler.append(ifade)
                parca = []
            else:
                parca.append(karakter)
        parca.append("\n")
    kalan = "".join(parca).strip()
    if kalan:
        ifadeler.append(kalan)
    return ifadeler


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Kullanim: python sql_calistir.py <dosya.sql>")
    dosya = Path(sys.argv[1])
    if not dosya.is_file():
        raise SystemExit(f"Dosya bulunamadi: {dosya}")

    ifadeler = [
        i for i in sql_ifadelerine_bol(dosya.read_text(encoding="utf-8"))
        if i.upper() not in ("BEGIN", "COMMIT")
    ]

    baglanti = engine.raw_connection()
    try:
        imlec = baglanti.cursor()
        for ifade in ifadeler:
            imlec.execute(ifade)
            if imlec.description:
                basliklar = [k[0] for k in imlec.description]
                print("\n" + " | ".join(basliklar))
                print("-" * 60)
                for satir in imlec.fetchall():
                    print(" | ".join("" if d is None else str(d) for d in satir))
            elif imlec.rowcount >= 0 and ifade.split()[0].upper() in ("UPDATE", "INSERT", "DELETE"):
                print(f"{ifade.split()[0].upper()}: {imlec.rowcount} satir")
        baglanti.commit()
        print(f"\nBASARILI: {dosya.name} calistirildi.")
    except Exception as hata:
        baglanti.rollback()
        print(f"\nHATA, hicbir degisiklik kaydedilmedi:\n{hata}")
        raise SystemExit(1)
    finally:
        baglanti.close()


if __name__ == "__main__":
    main()
