-- VoyageAI - Koordinatı eksik kalan 8 yer (hafta 2 verisinin tamamlanması)
--
-- Çalıştırma:  python sql_calistir.py sql/koordinat_eksik_8_yer.sql
--
-- Güvenlik:
--   * Sadece enlem/boylam'ı BOŞ olan satırlar güncellenir; dolu koordinat ezilmez.
--   * yer_id ile birlikte yer adı da kontrol edilir; ad tutmazsa satır değişmez.
--   * Hepsi tek işlemde (BEGIN/COMMIT) çalışır.

BEGIN;

-- 1) Kimlik kontrolü bekleyen 3 yer: OSM eşleşmesi doğru çıktı.
--    İsim farkı sadece dil farkıydı (Türkçe ad / yerel ad).
-- Miniatürk = "Miniatürk Açıkhava Müzesi" (OSM node 1352425761)
UPDATE yerler SET enlem = 41.059005, boylam = 28.9490675
 WHERE yer_id = 276 AND ad = 'Miniatürk Müzesi' AND enlem IS NULL AND boylam IS NULL;

-- Çarli Kontrol Noktası = "Checkpoint Charlie" (OSM node 417346627)
UPDATE yerler SET enlem = 52.5074321, boylam = 13.3903814
 WHERE yer_id = 324 AND ad = 'Çarli Kontrol Noktası' AND enlem IS NULL AND boylam IS NULL;

-- İstanbul Fotoğraf Müzesi = "Istanbul Photography Museum", Kadırga (OSM node 1807703751)
UPDATE yerler SET enlem = 41.0046397, boylam = 28.967754
 WHERE yer_id = 360 AND ad = 'İstanbul Fotoğraf Müzesi' AND enlem IS NULL AND boylam IS NULL;

-- 2) ARTER: eski OSM eşleşmesi YANLIŞTI (İstiklal'deki eski bina, bugün Meşher).
--    ARTER 2019'dan beri Dolapdere'de: Irmak Cd. No:13, Beyoğlu.
UPDATE yerler SET enlem = 41.04090, boylam = 28.97878
 WHERE yer_id = 278 AND ad = 'ARTER' AND enlem IS NULL AND boylam IS NULL;

-- 3) Hundertwasserhaus: koordinat doğruydu, OSM kaydında isim alanı boş olduğu için
--    aktarım scripti "format hatası" vermişti. OSM node 76469807.
UPDATE yerler SET enlem = 48.2074277, boylam = 16.3939296
 WHERE yer_id = 372 AND ad = 'Hundertwasserhaus' AND enlem IS NULL AND boylam IS NULL;

-- 4) Alan/şerit gibi tek noktası olmayan 3 yer: ziyaretçinin gittiği TEMSİLİ nokta.
-- Calanques Ulusal Parkı -> Sugiton seyir noktası (Marsilya içinden en çok kullanılan giriş;
--   koordinat Calanques Milli Parkı resmi sitesinden)
UPDATE yerler SET enlem = 43.214023, boylam = 5.448105
 WHERE yer_id = 48 AND ad = 'Calanques Ulusal Parkı' AND enlem IS NULL AND boylam IS NULL;

-- Nil Kıyısı Yürüyüş Alanı -> Kasr-ün Nil Köprüsü (Tahrir tarafı, akşam yürüyüşü noktası)
UPDATE yerler SET enlem = 30.043747, boylam = 31.229464
 WHERE yer_id = 233 AND ad = 'Nil Kıyısı Yürüyüş Alanı' AND enlem IS NULL AND boylam IS NULL;

-- Cenevre Gölü Kıyısı -> Quai du Mont-Blanc (göl kıyısı promenadı)
UPDATE yerler SET enlem = 46.209537, boylam = 6.151237
 WHERE yer_id = 170 AND ad = 'Cenevre Gölü Kıyısı' AND enlem IS NULL AND boylam IS NULL;

COMMIT;

-- Kontrol: 8 yer de dolu görünmeli
SELECT yer_id, ad, enlem, boylam
  FROM yerler
 WHERE yer_id IN (48, 170, 233, 276, 278, 324, 360, 372)
 ORDER BY yer_id;

-- Kontrol: hâlâ koordinatı boş yer kaldı mı?
SELECT COUNT(*) AS koordinati_bos_yer_sayisi
  FROM yerler
 WHERE enlem IS NULL OR boylam IS NULL;
