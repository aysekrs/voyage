"""VoyageAI 3. hafta: Aday koordinatlarla, VERITABANINI DEGISTIRMEDEN rota testi.
Bu konumlar dogrulanmis giris noktalari degildir; test amaclidir.
Dosyayi backend klasorune koyup python hafta3_aday_rota_test.py ile calistirin.
"""
import csv
from pathlib import Path
from sqlalchemy import text
from database import SessionLocal
from rota_algoritmasi import rota_olustur

SEHIRLER = [(1, "Istanbul"), (8, "Paris"), (24, "Berlin"), (39, "Amsterdam"), (82, "Viyana")]
GUN_SAYISI = 3
GUNLUK_DAKIKA = 5 * 60

# Yerler ana koordinatlarini onceliklendir; yoksa koordinat_adaylari tablosundan
# bir aday konum kullan. Adaylar ASLA dogrulanmis olarak isaretlenmez.
SORGU = text("""
SELECT y.yer_id AS id, y.ad, y.kategori, y.ziyaret_suresi,
       COALESCE(y.enlem, k.enlem) AS lat,
       COALESCE(y.boylam, k.boylam) AS lon,
       CASE WHEN y.enlem IS NOT NULL AND y.boylam IS NOT NULL
            THEN 'ana_tablo' ELSE 'aday_test' END AS kaynak
FROM yerler AS y
LEFT JOIN LATERAL (
    SELECT a.enlem, a.boylam
    FROM koordinat_adaylari a
    WHERE a.yer_id = y.yer_id
      AND a.enlem IS NOT NULL AND a.boylam IS NOT NULL
      AND a.enlem BETWEEN -90 AND 90
      AND a.boylam BETWEEN -180 AND 180
    ORDER BY a.enlem, a.boylam
    LIMIT 1
) AS k ON true
WHERE y.sehir_id = :sehir_id
ORDER BY y.yer_id
""")


def test_et(db, sehir_id, ad):
    kayitlar = db.execute(SORGU, {"sehir_id": sehir_id}).mappings().all()
    uygun = []
    eksik_koordinat = 0
    eksik_sure = 0
    for r in kayitlar:
        if (r["lat"] is None or r["lon"] is None
            or not (-90 <= r["lat"] <= 90 and -180 <= r["lon"] <= 180)):
            eksik_koordinat += 1
            continue
        if r["ziyaret_suresi"] is None or r["ziyaret_suresi"] <= 0:
            eksik_sure += 1
            continue
        uygun.append({
            "id": r["id"], "ad": r["ad"], "kategori": r["kategori"],
            "lat": r["lat"], "lon": r["lon"],
            "ziyaret_suresi": r["ziyaret_suresi"], "kaynak": r["kaynak"]
        })

    gunler = [{"yerler": [], "dakika": 0} for _ in range(GUN_SAYISI)]
    sigmayan = 0
    for yer in uygun:
        for gun in gunler:
            if gun["dakika"] + yer["ziyaret_suresi"] <= GUNLUK_DAKIKA:
                gun["yerler"].append(yer)
                gun["dakika"] += yer["ziyaret_suresi"]
                break
        else:
            sigmayan += 1

    toplam_mesafe = 0.0
    tum_idler = []
    aday_sayisi = 0
    for gun_no, gun in enumerate(gunler, start=1):
        sonuc = rota_olustur(gun["yerler"])
        rota = sonuc["rota"]
        toplam_mesafe += sonuc["son_mesafe_km"]
        tum_idler.extend(yer["id"] for yer in rota)
        aday_sayisi += sum(yer["kaynak"] == "aday_test" for yer in rota)
        durak_adlari = ', '.join(y["ad"] for y in rota) or '(bos)'
        print(f"  Gun {gun_no}: {len(rota)} yer, {gun['dakika']} dk -> {durak_adlari}")

    test_ok = (
        len(tum_idler) == len(set(tum_idler))
        and all(g["dakika"] <= GUNLUK_DAKIKA for g in gunler)
        and len(gunler) == GUN_SAYISI
        and len(tum_idler) > 0
    )
    return {
        "Sehir": ad,
        "Gun": GUN_SAYISI,
        "RotaDurak": len(tum_idler),
        "AdayKullanilanDurak": aday_sayisi,
        "ToplamMesafeKm": f"{toplam_mesafe:.3f}",
        "EksikKoordinat": eksik_koordinat,
        "EksikSure": eksik_sure,
        "SureyeSigmayan": sigmayan,
        "Sonuc": "TEST_BASARILI" if test_ok else "KONTROL_GEREKLI"
    }


def main():
    db = SessionLocal()
    try:
        rapor = []
        for sehir_id, sehir in SEHIRLER:
            print(f"\n=== {sehir} | 3 gun x 5 saat ===")
            sonuc = test_et(db, sehir_id, sehir)
            rapor.append(sonuc)
            print(f"=> {sonuc['RotaDurak']} durak, {sonuc['ToplamMesafeKm']} km; "
                  f"aday: {sonuc['AdayKullanilanDurak']}; {sonuc['Sonuc']}")

        cikti = Path(__file__).resolve().parent / "VoyageAI_3Hafta_Aday_Rota_Testleri.csv"
        with cikti.open('w', encoding='utf-8-sig', newline='') as dosya:
            yazici = csv.DictWriter(dosya, fieldnames=rapor[0].keys(), delimiter=';')
            yazici.writeheader()
            yazici.writerows(rapor)
        print(f"\nCSV kaydedildi: {cikti}")
        print('UYARI: Aday koordinatlar dogrulanmis ziyaret/giris noktasi degildir.')
        print('Ana veritabanindaki hicbir kayit degistirilmedi.')
    finally:
        db.close()


if __name__ == '__main__':
    main()
