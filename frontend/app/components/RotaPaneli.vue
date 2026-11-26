<script setup lang="ts">
import { ref, computed, watch } from "vue";

interface RotaYeri {
  order: number;
  place_id: number;
  name: string;
  category: string | null;
  latitude: number;
  longitude: number;
  visit_minutes: number;
  distance_from_previous_km: number;
  travel_minutes: number;
}

interface Gun {
  day: number;
  places: RotaYeri[];
  visit_minutes: number;
  travel_minutes: number;
  total_minutes: number;
  distance_km: number;
  distance_before_2opt_km: number;
}

interface RotaCevabi {
  test_mode?: boolean;
  coordinate_source?: string;
  city: string;
  days: number;
  hours_per_day: number;
  total_distance_km: number;
  total_travel_minutes: number;
  routed_places: number;
  itinerary: Gun[];
  excluded: {
    missing_or_invalid_coordinates: number;
    missing_visit_duration: number;
    not_fitting_in_days: number;
  };
  not_fitting_places?: { place_id: number; name: string; visit_minutes: number }[];
  warning: string;
}

type KayitliRota = Partial<RotaCevabi> & {
  itinerary_id?: number;
  city_id?: number;
  destination_id?: number;
  itinerary?: Array<Partial<Gun> & { places?: Partial<RotaYeri>[] }>;
};

const props = defineProps<{ cityId: number }>();

const gunSayisi = ref(3);
const gunlukSaat = ref(5);
const aktifGun = ref(0);
const rota = ref<RotaCevabi | null>(null);
const adayTestModu = ref(false);
const aktifRotaTest = ref(false);
const yukleniyor = ref(false);
const kaydediliyor = ref(false);
const kayitAciliyor = ref(false);
const hata = ref("");
const bildirim = ref("");
const kayitNo = ref<number | null>(null);
const acilacakKayitNo = ref<number | null>(null);

let istekNo = 0;
const API = "http://127.0.0.1:8001";

const seciliGun = computed(() => rota.value?.itinerary[aktifGun.value] ?? null);
const durakSayisi = computed(() => rota.value?.itinerary.reduce((a, g) => a + g.places.length, 0) ?? 0);

function sureYaz(dakika: number): string {
  const dk = Math.round(dakika);
  if (dk < 60) return `${dk} dk`;
  const saat = Math.floor(dk / 60);
  const kalan = dk % 60;
  return kalan ? `${saat} sa ${kalan} dk` : `${saat} sa`;
}

function sayi(deger: unknown, varsayilan = 0): number {
  const n = Number(deger);
  return Number.isFinite(n) ? n : varsayilan;
}

function kmMesafesi(yer1: RotaYeri, yer2: RotaYeri): number {
  const R = 6371;
  const rad = (x: number) => (x * Math.PI) / 180;
  const dLat = rad(yer2.latitude - yer1.latitude);
  const dLon = rad(yer2.longitude - yer1.longitude);
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(rad(yer1.latitude)) * Math.cos(rad(yer2.latitude)) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.atan2(Math.sqrt(a), Math.sqrt(Math.max(0, 1 - a)));
}

// GET cevabında distance_km veya excluded yoksa haritanın bozulmamasını sağlar.
function kayitliRotayiDuzenle(veri: KayitliRota): RotaCevabi {
  const gunler: Gun[] = (veri.itinerary ?? []).map((g, indeks) => {
    const yerler: RotaYeri[] = (g.places ?? []).map((y, i) => ({
      order: sayi(y.order, i + 1),
      place_id: sayi(y.place_id),
      name: String(y.name ?? "İsimsiz yer"),
      category: y.category ?? null,
      latitude: sayi(y.latitude),
      longitude: sayi(y.longitude),
      visit_minutes: sayi(y.visit_minutes),
      distance_from_previous_km: sayi(y.distance_from_previous_km),
      travel_minutes: sayi(y.travel_minutes)
    }));
    let mesafe = 0;
    for (let i = 1; i < yerler.length; i++) {
      // API'den gelen değer varsa onu kullan, yoksa koordinatlardan hesapla.
      if (yerler[i].distance_from_previous_km === 0) {
        yerler[i].distance_from_previous_km = Number(kmMesafesi(yerler[i - 1], yerler[i]).toFixed(3));
      }
      mesafe += yerler[i].distance_from_previous_km;
    }
    const ziyaret = sayi(g.visit_minutes, yerler.reduce((a, y) => a + y.visit_minutes, 0));
    const yol = sayi(g.travel_minutes, yerler.reduce((a, y) => a + y.travel_minutes, 0));
    return {
      day: sayi(g.day, indeks + 1),
      places: yerler,
      visit_minutes: ziyaret,
      travel_minutes: yol,
      total_minutes: sayi(g.total_minutes, ziyaret + yol),
      distance_km: sayi(g.distance_km, mesafe),
      distance_before_2opt_km: sayi(g.distance_before_2opt_km, mesafe)
    };
  });
  const toplamMesafe = gunler.reduce((a, g) => a + g.distance_km, 0);
  return {
    city: String(veri.city ?? "Kayıtlı rota"),
    days: sayi(veri.days, gunler.length),
    hours_per_day: sayi(veri.hours_per_day, 5),
    total_distance_km: sayi(veri.total_distance_km, toplamMesafe),
    total_travel_minutes: sayi(veri.total_travel_minutes, gunler.reduce((a, g) => a + g.travel_minutes, 0)),
    routed_places: sayi(veri.routed_places, gunler.reduce((a, g) => a + g.places.length, 0)),
    itinerary: gunler,
    excluded: {
      missing_or_invalid_coordinates: sayi(veri.excluded?.missing_or_invalid_coordinates),
      missing_visit_duration: sayi(veri.excluded?.missing_visit_duration),
      not_fitting_in_days: sayi(veri.excluded?.not_fitting_in_days)
    },
    warning: String(veri.warning ?? "Kaydedilmiş rota görüntüleniyor.")
  };
}

async function rotaGetir() {
  const buIstek = ++istekNo;
  yukleniyor.value = true;
  hata.value = "";
  bildirim.value = "";
  rota.value = null;
  aktifRotaTest.value = false;
  kayitNo.value = null;
  aktifGun.value = 0;
  try {
    const params = new URLSearchParams({
      days: String(gunSayisi.value),
      hours_per_day: String(gunlukSaat.value),
      include_candidates: String(adayTestModu.value)
    });
    const cevap = await fetch(`${API}/destinations/${props.cityId}/route?${params}`);
    if (!cevap.ok) throw new Error(`API hatası: ${cevap.status}`);
    const sonuc: RotaCevabi = await cevap.json();
    if (buIstek !== istekNo) return;
    rota.value = sonuc;
    aktifRotaTest.value = sonuc.test_mode === true;
  } catch (error) {
    if (buIstek !== istekNo) return;
    hata.value = "Rota oluşturulamadı. FastAPI bağlantısını kontrol et.";
    console.error(error);
  } finally {
    if (buIstek === istekNo) yukleniyor.value = false;
  }
}

async function rotaKaydet() {
  if (!rota.value || durakSayisi.value === 0 || kaydediliyor.value || aktifRotaTest.value) return;
  kaydediliyor.value = true;
  hata.value = "";
  bildirim.value = "";
  const mevcutSehir = props.cityId;
  try {
    const params = new URLSearchParams({
      destination_id: String(props.cityId),
      days: String(gunSayisi.value),
      hours_per_day: String(gunlukSaat.value)
    });
    // POST, backend'deki kayıt servisi tarafından rotayı yeniden üretip kaydeder.
    const cevap = await fetch(`${API}/itineraries?${params}`, { method: "POST" });
    if (!cevap.ok) throw new Error(`Kayıt hatası: ${cevap.status} - ${await cevap.text()}`);
    const veri = await cevap.json();
    if (mevcutSehir !== props.cityId) return;
    const id = Number(veri.itinerary_id);
    if (!Number.isInteger(id) || id < 1) throw new Error("Geçerli kayıt numarası gelmedi.");
    kayitNo.value = id;
    acilacakKayitNo.value = id;
    bildirim.value = `Rota kaydedildi. Kayıt numarası: ${id}`;
  } catch (error) {
    hata.value = "Rota kaydedilemedi. Backend bağlantısını ve terminali kontrol et.";
    console.error(error);
  } finally {
    kaydediliyor.value = false;
  }
}

async function kayitliRotaAc() {
  const id = Number(acilacakKayitNo.value);
  if (!Number.isInteger(id) || id <= 0 || kayitAciliyor.value) {
    hata.value = "Geçerli bir kayıt numarası gir.";
    return;
  }
  const buIstek = ++istekNo;
  kayitAciliyor.value = true;
  hata.value = "";
  bildirim.value = "";
  try {
    const cevap = await fetch(`${API}/itineraries/${id}`);
    if (!cevap.ok) throw new Error(`Kayıt açılamadı: ${cevap.status}`);
    const veri: KayitliRota = await cevap.json();
    if (buIstek !== istekNo) return;
    const kayitSehirId = veri.city_id ?? veri.destination_id;
    if (kayitSehirId != null && Number(kayitSehirId) !== props.cityId) {
      throw new Error("Kayıt başka bir şehre ait. Önce ilgili şehri seç.");
    }
    const sonuc = kayitliRotayiDuzenle(veri);
    rota.value = sonuc;
    aktifRotaTest.value = false;
    gunSayisi.value = sonuc.days;
    gunlukSaat.value = sonuc.hours_per_day;
    aktifGun.value = 0;
    kayitNo.value = id;
    bildirim.value = `${id} numaralı kayıtlı rota açıldı.`;
  } catch (error) {
    if (buIstek !== istekNo) return;
    hata.value = error instanceof Error ? error.message : "Kayıtlı rota açılamadı.";
    console.error(error);
  } finally {
    kayitAciliyor.value = false;
  }
}

watch(() => props.cityId, () => {
  istekNo++;
  rota.value = null;
  aktifRotaTest.value = false;
  hata.value = "";
  bildirim.value = "";
  kayitNo.value = null;
  yukleniyor.value = false;
  aktifGun.value = 0;
});

function ayarlarDegisti() {
  istekNo++;
  rota.value = null;
  aktifRotaTest.value = false;
  kayitNo.value = null;
  hata.value = "";
  bildirim.value = "";
  aktifGun.value = 0;
}
</script>

<template>
  <section class="b-bolum">
    <p class="v-ust-yazi">Rota</p>
    <h2 class="v-baslik">Akıllı rota planlayıcı</h2>
    <p class="b-aciklama">Gün sayısını ve günlük gezi süresini seç. VoyageAI yakın yerleri aynı güne toplayıp ziyaret sırasını hesaplar.</p>

    <div class="b-alanlar">
      <div>
        <label for="rota-gun" class="b-etiket">Gün sayısı <strong>{{ gunSayisi }} gün</strong></label>
        <input id="rota-gun" v-model.number="gunSayisi" type="range" min="1" max="7"
          class="b-kaydirici" @input="ayarlarDegisti" />
      </div>
      <div>
        <label for="rota-saat" class="b-etiket">Günlük süre <strong>{{ gunlukSaat }} saat</strong></label>
        <input id="rota-saat" v-model.number="gunlukSaat" type="range" min="1" max="12"
          class="b-kaydirici" @input="ayarlarDegisti" />
      </div>
    </div>

    <div class="b-butonlar">
      <button type="button" class="v-buton" :disabled="yukleniyor" @click="rotaGetir">
        {{ yukleniyor ? "Hesaplanıyor..." : "Rotayı oluştur" }}
      </button>
      <button type="button" class="v-buton-ikincil"
        :disabled="!rota || durakSayisi === 0 || kaydediliyor || kayitAciliyor || aktifRotaTest"
        @click="rotaKaydet">
        {{ kaydediliyor ? "Kaydediliyor..." : "Rotayı kaydet" }}
      </button>
    </div>

    <div class="b-kayit">
      <div>
        <label for="kayit-numarasi">Kayıt numarası</label>
        <input id="kayit-numarasi" v-model.number="acilacakKayitNo" type="number" min="1"
          class="b-girdi" placeholder="Örn. 1" />
      </div>
      <button type="button" class="v-buton-ikincil" :disabled="kayitAciliyor" @click="kayitliRotaAc">
        {{ kayitAciliyor ? "Açılıyor..." : "Kayıtlı rotayı aç" }}
      </button>
    </div>

    <p v-if="aktifRotaTest" class="b-uyari" role="status">
      Test rotası: aday koordinatlar doğrulanmamıştır, kaydetme kapalıdır.
    </p>
    <p v-if="bildirim" class="b-basari" role="status">{{ bildirim }}</p>
    <p v-if="hata" class="b-hata" role="alert">{{ hata }}</p>

    <div v-if="rota">
      <div class="b-ozet">
        <div class="b-ozet-kart">
          <span>Kuş uçuşu mesafe</span>
          <strong>{{ rota.total_distance_km.toFixed(1) }} km</strong>
        </div>
        <div class="b-ozet-kart">
          <span>Tahmini yol süresi</span>
          <strong>{{ sureYaz(rota.total_travel_minutes) }}</strong>
        </div>
        <div class="b-ozet-kart">
          <span>Durak sayısı</span>
          <strong>{{ durakSayisi }}</strong>
        </div>
        <div class="b-ozet-kart">
          <span>Planlanan gün</span>
          <strong>{{ rota.days }}</strong>
        </div>
      </div>

      <div class="b-sekmeler">
        <button v-for="(gun, index) in rota.itinerary" :key="gun.day" type="button"
          :class="['v-cip', { aktif: aktifGun === index }]" @click="aktifGun = index">
          Gün {{ gun.day }}
        </button>
      </div>

      <div v-if="seciliGun" class="b-gun">
        <h3>{{ seciliGun.day }}. gün</h3>
        <p class="b-gun-ozet">
          Ziyaret {{ sureYaz(seciliGun.visit_minutes) }} · Yol ~{{ sureYaz(seciliGun.travel_minutes) }} ·
          <strong>Toplam {{ sureYaz(seciliGun.total_minutes) }}</strong> · {{ seciliGun.distance_km.toFixed(1) }} km
        </p>
        <p v-if="seciliGun.places.length === 0" class="b-not">
          Bu güne yer kalmadı. Günlük süreyi azaltabilir ya da gün sayısını düşürebilirsin.
        </p>
        <div v-for="yer in seciliGun.places" :key="yer.place_id" class="b-durak">
          <span class="b-durak-no">{{ yer.order }}</span>
          <div>
            <p class="b-durak-ad">{{ yer.name }}</p>
            <p class="b-durak-alt">{{ yer.category ?? "Kategori belirtilmedi" }}</p>
            <p v-if="yer.order > 1" class="b-durak-yol">
              {{ yer.distance_from_previous_km <= 1.5 ? "🚶" : "🚇" }}
              Önceki duraktan {{ yer.distance_from_previous_km }} km · ~{{ yer.travel_minutes }} dk
            </p>
            <p v-else class="b-durak-yol">Günün başlangıç noktası</p>
          </div>
          <span class="b-durak-sure">{{ sureYaz(yer.visit_minutes) }}</span>
        </div>
        <ClientOnly>
          <RotaHaritasi v-if="seciliGun.places.length > 0" :key="`${cityId}-${seciliGun.day}-${kayitNo ?? 'yeni'}`" :places="seciliGun.places" />
        </ClientOnly>
      </div>

      <div v-if="rota.excluded.not_fitting_in_days > 0" class="b-bilgi">
        <p><strong>{{ rota.excluded.not_fitting_in_days }} yer seçtiğin süreye sığmadı</strong>
          ({{ rota.days }} gün × {{ rota.hours_per_day }} saat).</p>
        <p>Hepsini görmek için gün sayısını veya günlük süreyi artırıp rotayı yeniden oluştur.</p>
        <p v-if="rota.not_fitting_places?.length">
          Bu rotaya girmeyenler: {{ rota.not_fitting_places.map((y) => y.name).join(", ") }}
        </p>
      </div>
      <p v-if="rota.excluded.missing_or_invalid_coordinates + rota.excluded.missing_visit_duration > 0" class="b-uyari">
        Verisi eksik olduğu için rotaya alınamayan:
        <span v-if="rota.excluded.missing_or_invalid_coordinates">{{ rota.excluded.missing_or_invalid_coordinates }} yerin koordinatı yok</span>
        <span v-if="rota.excluded.missing_or_invalid_coordinates && rota.excluded.missing_visit_duration"> · </span>
        <span v-if="rota.excluded.missing_visit_duration">{{ rota.excluded.missing_visit_duration }} yerin ziyaret süresi yok</span>
      </p>
      <p class="b-not">{{ rota.warning }}</p>
    </div>
  </section>
</template>
