"""VoyageAI hafta 2 - staging verisini guvenli sekilde ilerlet.

Kullanim (backend klasorune kopyaladiktan sonra):
  .\venv\Scripts\python.exe voyageai_hafta2_veri_hazirlik.py

Yalnizca yeni_yer_adaylari tablosuna tahmini ziyaret suresi ekler.
Fiyat ve koordinatlari ONAYLAMAZ; ana yerler/sehirler tablolarina DOKUNMAZ.
"""
from sqlalchemy import text
from database import SessionLocal

SURELER = {"tarih": 90, "doğa": 75, "yemek": 60, "gece_hayati": 120}


def main():
    with SessionLocal.begin() as db:
        table = db.execute(text("SELECT to_regclass('public.yeni_yer_adaylari')")).scalar_one()
        if table is None:
            raise SystemExit("'yeni_yer_adaylari' tablosu bulunamadi. Once aday aktarim dosyasini calistir.")

        db.execute(text("ALTER TABLE yeni_yer_adaylari ADD COLUMN IF NOT EXISTS ziyaret_suresi_turu TEXT"))

        # Kategorisi tanimli ve daha once sure girilmemis adaylarda SADECE tahmini sureyi doldur.
        for kategori, dakika in SURELER.items():
            db.execute(text("""
                UPDATE yeni_yer_adaylari
                   SET ziyaret_suresi = :dakika,
                       ziyaret_suresi_turu = 'KATEGORI_TAHMINI'
                 WHERE kategori = :kategori
                   AND ziyaret_suresi IS NULL
                   AND kayit_onayi = FALSE
            """), {"dakika": dakika, "kategori": kategori})

        oz = db.execute(text("""
            SELECT sehir_adi, COUNT(*) AS aday,
                   COUNT(*) FILTER (WHERE ziyaret_suresi IS NOT NULL) AS sure_var,
                   COUNT(*) FILTER (WHERE ziyaret_suresi_turu = 'KATEGORI_TAHMINI') AS tahmini_sure,
                   COUNT(*) FILTER (WHERE ortalama_ucret IS NOT NULL) AS ucret_var,
                   COUNT(*) FILTER (WHERE koordinat_dogrulandi = TRUE) AS konum_onayli,
                   COUNT(*) FILTER (WHERE kayit_onayi = TRUE) AS kayit_onayli
              FROM yeni_yer_adaylari
             GROUP BY sehir_adi ORDER BY sehir_adi
        """)).mappings().all()
        print("\nVOYAGEAI - HAFTA 2 ADAY VERI DURUMU")
        print("Sehir | Aday | Sure var | Tahmin | Ucret var | Konum onayli | Kayit onayli")
        for r in oz:
            print(f"{r['sehir_adi']} | {r['aday']} | {r['sure_var']} | {r['tahmini_sure']} | {r['ucret_var']} | {r['konum_onayli']} | {r['kayit_onayli']}")
        print("\nUYARI: Tahmini sureler dogrulanmis ziyaret suresi degildir.")
        print("'yerler' ve 'sehirler' tablolarina dokunulmadi. Fiyat/konum onayi verilmedi.")

if __name__ == '__main__':
    main()
