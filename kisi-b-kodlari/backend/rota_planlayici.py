"""VoyageAI - yerleri günlere bölme ve yol süresi tahmini (hafta 3-4).

Bu dosya veritabanına bağlanmaz; sadece hesap yapar. Bu yüzden
tests/test_rota.py ile veritabanı olmadan test edilebilir.

Yöntem:
1. Bütün yerler Nearest Neighbor + 2-opt ile tek bir tura dizilir.
   Böylece birbirine yakın yerler turda art arda gelir.
2. Tur sırayla günlere doldurulur: ziyaret süresi + yol süresi günlük
   limiti aşınca bir sonraki güne geçilir. Her gün haritada tek bir
   bölgeye düşer; şehrin iki ucu aynı güne karışmaz.
3. Her günün kendi içindeki sırası tekrar NN + 2-opt ile iyileştirilir.
"""
from rota_algoritmasi import haversine, rota_olustur

# Kuş uçuşu mesafe gerçek yoldan kısadır; şehir içi ortalama sapma payı.
YOL_KATSAYISI = 1.3
# Bu mesafeye kadar yürünür, üstünde toplu taşıma/taksi varsayılır.
YURUME_SINIRI_KM = 1.5
YURUME_HIZI_KMSA = 4.5
TOPLU_TASIMA_HIZI_KMSA = 18.0
TOPLU_TASIMA_BEKLEME_DK = 10


def yol_suresi_dk(kus_ucusu_km: float) -> int:
    """İki durak arası tahmini yol süresi (dakika). Gerçek yol tarifi değildir."""
    if kus_ucusu_km <= 0:
        return 0
    if kus_ucusu_km <= YURUME_SINIRI_KM:
        return max(1, round(_yurume_dk(kus_ucusu_km)))
    toplu_tasima = TOPLU_TASIMA_BEKLEME_DK + kus_ucusu_km * YOL_KATSAYISI / TOPLU_TASIMA_HIZI_KMSA * 60
    # Sınırın hemen üstü, sınırdaki yürüyüşten kısa sürmesin (süre mesafeyle azalmamalı).
    return round(max(toplu_tasima, _yurume_dk(YURUME_SINIRI_KM)))


def _yurume_dk(kus_ucusu_km: float) -> float:
    return kus_ucusu_km * YOL_KATSAYISI / YURUME_HIZI_KMSA * 60


def _mesafe(a: dict, b: dict) -> float:
    return haversine(a["lat"], a["lon"], b["lat"], b["lon"])


def gunlere_bol(yerler: list[dict], gun_sayisi: int, gunluk_dk: int) -> tuple[list[list[dict]], list[dict]]:
    """Yerleri günlere böler.

    yerler: her biri en az {"id", "lat", "lon", "ziyaret_suresi"} içeren sözlükler.
    Döner: (gunler, sigmayanlar). gunler uzunluğu her zaman gun_sayisi'dır.
    """
    gunler: list[list[dict]] = [[] for _ in range(gun_sayisi)]
    if not yerler or gun_sayisi <= 0:
        return gunler, list(yerler)

    tur = rota_olustur(list(yerler))["rota"]

    # Her şey rahat sığıyorsa yükü günlere dengeli dağıt (ilk günler dolup
    # son günler boş kalmasın). Sığmıyorsa hedef = günlük limit.
    tur_toplam_dk = gun_toplam_dk(tur)
    hedef_dk = min(gunluk_dk, -(-tur_toplam_dk * 11 // (10 * gun_sayisi)))

    sigmayanlar: list[dict] = []
    gun_no = 0
    kullanilan_dk = 0
    for yer in tur:
        sure = yer["ziyaret_suresi"]
        if sure > gunluk_dk:
            # Tek başına bir güne bile sığmıyor.
            sigmayanlar.append(yer)
            continue

        while True:
            bugun = gunler[gun_no]
            son_gun = gun_no == gun_sayisi - 1
            yol = yol_suresi_dk(_mesafe(bugun[-1], yer)) if bugun else 0
            sinir = gunluk_dk if son_gun else hedef_dk
            if kullanilan_dk + yol + sure <= sinir or (not bugun and sure <= gunluk_dk):
                bugun.append(yer)
                kullanilan_dk += yol + sure
                break
            if son_gun:
                # Son gün doldu: bu yeri atla, sıradaki (belki daha kısa) yerleri dene.
                sigmayanlar.append(yer)
                break
            gun_no += 1
            kullanilan_dk = 0

    # Gün içi sırayı iyileştir; 2-opt yol süresini artırmaz ama
    # yine de limit aşılırsa sondaki yeri çıkar (güvenlik).
    for i, gun in enumerate(gunler):
        sirali = rota_olustur(gun)["rota"]
        while sirali and gun_toplam_dk(sirali) > gunluk_dk:
            sigmayanlar.append(sirali.pop())
        gunler[i] = sirali

    return gunler, sigmayanlar


def gun_toplam_dk(gun: list[dict]) -> int:
    """Bir günün ziyaret + yol süresi toplamı (dakika)."""
    toplam = sum(y["ziyaret_suresi"] for y in gun)
    for onceki, sonraki in zip(gun, gun[1:]):
        toplam += yol_suresi_dk(_mesafe(onceki, sonraki))
    return toplam
