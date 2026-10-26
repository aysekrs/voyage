
import csv
from pathlib import Path
from collections import Counter

from sqlalchemy import select

from database import SessionLocal
from city_models import Sehir, Yer


KLASOR = Path(__file__).resolve().parent

GIRIS = KLASOR / "voyageai_iki_tur_karsilastirma.csv"
CIKIS = KLASOR / "koordinat_on_kontrol.csv"


def temizle(deger):
    return " ".join(str(deger or "").strip().casefold().split())


def anahtar(ulke, sehir, yer):
    return (
        temizle(ulke),
        temizle(sehir),
        temizle(yer)
    )


def koordinat_oku(enlem, boylam):
    try:
        lat = float(enlem)
        lon = float(boylam)

        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return (lat, lon)

    except (ValueError, TypeError):
        pass

    return None


def main():
    if not GIRIS.exists():
        print("CSV bulunamadi:", GIRIS)
        return

    # Geoapify sonuçlarını oku.
    with GIRIS.open(
        "r", encoding="utf-8-sig", newline=""
    ) as dosya:
        adaylar = list(csv.DictReader(dosya))

    # Her ülke, şehir ve yer için adayları grupla.
    aday_indeksi = {}

    for aday in adaylar:
        key = anahtar(
            aday["ulke"],
            aday["sehir"],
            aday["ad"]
        )

        aday_indeksi.setdefault(key, []).append(aday)

    db = SessionLocal()

    try:
        sorgu = (
            select(
                Yer.yer_id,
                Yer.ad.label("yer_adi"),
                Yer.enlem,
                Yer.boylam,
                Sehir.ad.label("sehir"),
                Sehir.ulke
            )
            .join(Sehir, Yer.sehir_id == Sehir.sehir_id)
            .order_by(Sehir.ulke, Sehir.ad, Yer.ad)
        )

        tum_yerler = db.execute(sorgu).all()

        sonuclar = []

        for yer in tum_yerler:

            # Koordinatı tamamlanmış yerleri atla.
            if yer.enlem is not None and yer.boylam is not None:
                continue

            key = anahtar(
                yer.ulke,
                yer.sehir,
                yer.yer_adi
            )

            eslesmeler = aday_indeksi.get(key, [])

            durum = ""
            aday = {}
            onerilen = None

            if len(eslesmeler) == 0:
                durum = "CSV_ESLESMEDI"

            elif len(eslesmeler) > 1:
                durum = "BIRDEN_FAZLA_CSV_KAYDI"

            else:
                aday = eslesmeler[0]

                ilk = koordinat_oku(
                    aday.get("ilk_tur_enlem"),
                    aday.get("ilk_tur_boylam")
                )

                ikinci = koordinat_oku(
                    aday.get("ikinci_tur_enlem"),
                    aday.get("ikinci_tur_boylam")
                )

                onayli = koordinat_oku(
                    aday.get("onayli_enlem"),
                    aday.get("onayli_boylam")
                )

                if onayli:
                    durum = "ONAYLI_CSV_KONTROL"
                    onerilen = onayli

                elif ilk and ikinci:
                    # Yaklaşık 0.001 derece fark toleransı.
                    yakin = (
                        abs(ilk[0] - ikinci[0]) <= 0.001
                        and abs(ilk[1] - ikinci[1]) <= 0.001
                    )

                    if yakin:
                        durum = "IKI_TUR_UYUMLU_KONTROL"
                        onerilen = ikinci
                    else:
                        durum = "FARKLI_ADAYLAR"
                        onerilen = ikinci

                elif ikinci:
                    durum = "SADECE_IKINCI_TUR"
                    onerilen = ikinci

                elif ilk:
                    durum = "SADECE_ILK_TUR"
                    onerilen = ilk

                else:
                    durum = "ADAY_BULUNAMADI"

            sonuclar.append({
                "yer_id": yer.yer_id,
                "ulke": yer.ulke,
                "sehir": yer.sehir,
                "yer_adi": yer.yer_adi,
                "durum": durum,
                "aday_enlem": onerilen[0] if onerilen else "",
                "aday_boylam": onerilen[1] if onerilen else "",
                "ilk_tur_adres": aday.get(
                    "ilk_tur_adres", ""
                ),
                "ikinci_tur_adres": aday.get(
                    "ikinci_tur_adres", ""
                ),
                "ikinci_tur_puan": aday.get(
                    "ikinci_tur_puan", ""
                ),
                "harita_kontrolu": "BEKLIYOR",
                "onayli_enlem": "",
                "onayli_boylam": ""
            })

        alanlar = [
            "yer_id",
            "ulke",
            "sehir",
            "yer_adi",
            "durum",
            "aday_enlem",
            "aday_boylam",
            "ilk_tur_adres",
            "ikinci_tur_adres",
            "ikinci_tur_puan",
            "harita_kontrolu",
            "onayli_enlem",
            "onayli_boylam"
        ]

        with CIKIS.open(
            "w", encoding="utf-8-sig", newline=""
        ) as dosya:
            writer = csv.DictWriter(
                dosya, fieldnames=alanlar
            )
            writer.writeheader()
            writer.writerows(sonuclar)

        sayilar = Counter(
            kayit["durum"] for kayit in sonuclar
        )

        print("\nVOYAGEAI KOORDINAT ON KONTROL")
        print("-----------------------------")
        print("Veritabanindaki toplam yer:", len(tum_yerler))
        print("Koordinati eksik yer:", len(sonuclar))
        print("CSV aday satiri:", len(adaylar))

        print("\nDurum dagilimi:")

        for durum, adet in sayilar.most_common():
            print(f"{durum}: {adet}")

        print("\nDosya olusturuldu:", CIKIS.name)
        print("Veritabani DEGISTIRILMEDI.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
