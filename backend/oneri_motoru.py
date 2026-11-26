
import csv
from pathlib import Path

DOSYA = Path(__file__).resolve().parent / "sehir_puanlama_taslagi.csv"

KATEGORILER = {
    "doga": "doga_sayisi",
    "yemek": "yemek_sayisi",
    "tarih": "tarih_sayisi",
    "gece": "gece_hayati_sayisi",
}


def oneri_hesapla(tercihler, minimum_yer=5):
    toplam_agirlik = sum(tercihler.values())

    if toplam_agirlik <= 0:
        raise ValueError("En az bir tercih 0'dan büyük olmalı.")

    sonuclar = []

    with DOSYA.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for sehir in reader:
            toplam_yer = int(sehir["toplam_yer"])

            # Çok az kayıtlı şehirleri ilk testten çıkarıyoruz.
            if toplam_yer < minimum_yer:
                continue

            puan = 0

            for kategori, sutun in KATEGORILER.items():
                yer_sayisi = int(sehir[sutun])

                oran = yer_sayisi / toplam_yer
                agirlik = tercihler[kategori]

                puan += oran * agirlik

            puan = (puan / toplam_agirlik) * 100

            sonuclar.append({
                "sehir": sehir["sehir"],
                "ulke": sehir["ulke"],
                "puan": round(puan, 2),
                "toplam_yer": toplam_yer
            })

    sonuclar.sort(
        key=lambda s: (-s["puan"], -s["toplam_yer"], s["sehir"])
    )

    return sonuclar


if __name__ == "__main__":

    # Örnek kullanıcının tercihleri
    tercihler = {
    "doga": 30,
    "yemek": 20,
    "tarih": 40,
    "gece": 10
}

    oneriler = oneri_hesapla(tercihler)

    print("\nVoyageAI - Ilk Oneri Motoru")
    print("----------------------------")

    for sira, sonuc in enumerate(oneriler[:5], start=1):
        print(
            f"{sira}. {sonuc['sehir']} "
            f"({sonuc['ulke']}) - "
            f"Uyum: {sonuc['puan']} - "
            f"Kayitli yer: {sonuc['toplam_yer']}"
        )

    print("\nNot: Sonuclar sadece kayitli yerlerin")
    print("kategori dagilimina dayanan prototip onerilerdir.")
