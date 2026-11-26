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
  <section class="mt-10 rounded-2xl bg-white p-6 shadow">
    <h2 class="text-2xl font-bold text-slate-800">🧭 Akıllı Rota Planlayıcı</h2>
    <p class="mt-2 text-gray-600">Gün sayısını ve günlük gezi süresini belirle. VoyageAI ziyaret sırasını hesaplasın.</p>

    <div class="mt-6 grid gap-6 md:grid-cols-2">
      <div>
        <label for="rota-gun" class="font-semibold">Gün sayısı: {{ gunSayisi }}</label>
        <input id="rota-gun" v-model.number="gunSayisi" type="range" min="1" max="7"
          class="mt-3 w-full accent-blue-600" @input="ayarlarDegisti" />
      </div>
      <div>
        <label for="rota-saat" class="font-semibold">Günlük süre: {{ gunlukSaat }} saat</label>
        <input id="rota-saat" v-model.number="gunlukSaat" type="range" min="1" max="12"
          class="mt-3 w-full accent-blue-600" @input="ayarlarDegisti" />
      </div>
    </div>

    <label class="mt-5 flex items-start gap-2 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">
      <input v-model="adayTestModu" type="checkbox" class="mt-1" @change="ayarlarDegisti" />
      <span><strong>Aday koordinatlarla test rotası oluştur</strong> — 11 ülkedeki şehirlerin haritasını denemek içindir. Konumlar henüz doğrulanmamıştır.</span>
    </label>

    <div class="mt-6 flex flex-wrap items-center gap-3">
      <button type="button" :disabled="yukleniyor" @click="rotaGetir"
        class="rounded-xl bg-blue-600 px-6 py-3 font-semibold text-white hover:bg-blue-700 disabled:opacity-50">
        {{ yukleniyor ? "Hesaplanıyor..." : "🧭 Rotayı Oluştur" }}
      </button>
      <button type="button" :disabled="!rota || durakSayisi === 0 || kaydediliyor || kayitAciliyor || aktifRotaTest"
        @click="rotaKaydet"
        class="rounded-xl bg-emerald-600 px-6 py-3 font-semibold text-white hover:bg-emerald-700 disabled:opacity-50">
        {{ kaydediliyor ? "Kaydediliyor..." : "💾 Rotayı Kaydet" }}
      </button>
    </div>

    <div class="mt-5 flex flex-wrap items-end gap-3 rounded-xl bg-slate-50 p-4">
      <div>
        <label for="kayit-numarasi" class="block text-sm font-semibold text-slate-700">Kayıt numarası</label>
        <input id="kayit-numarasi" v-model.number="acilacakKayitNo" type="number" min="1"
          class="mt-1 w-36 rounded-lg border border-slate-300 px-3 py-2" placeholder="Örn. 1" />
      </div>
      <button type="button" :disabled="kayitAciliyor" @click="kayitliRotaAc"
        class="rounded-xl bg-slate-800 px-5 py-2.5 font-semibold text-white hover:bg-slate-900 disabled:opacity-50">
        {{ kayitAciliyor ? "Açılıyor..." : "📂 Kayıtlı Rotayı Aç" }}
      </button>
    </div>

    <p v-if="aktifRotaTest" class="mt-4 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm font-semibold text-amber-900" role="status">
      TEST ROTASI: Aday koordinatlar doğrulanmamıştır. Bu rota gerçek yol tarifi değildir; veritabanına kaydetme kapalıdır.
    </p>
    <p v-if="bildirim" class="mt-4 text-green-700" role="status">{{ bildirim }}</p>
    <p v-if="hata" class="mt-4 text-red-600" role="alert">{{ hata }}</p>

    <div v-if="rota" class="mt-8">
      <div class="grid gap-3 md:grid-cols-4">
        <div class="rounded-xl bg-blue-50 p-4">
          <p class="text-sm text-gray-600">Kuş uçuşu mesafe</p>
          <p class="text-2xl font-bold text-purple-700">{{ rota.total_distance_km.toFixed(2) }} km</p>
        </div>
        <div class="rounded-xl bg-blue-50 p-4">
          <p class="text-sm text-gray-600">Tahmini yol süresi</p>
          <p class="text-2xl font-bold text-purple-700">{{ sureYaz(rota.total_travel_minutes) }}</p>
        </div>
        <div class="rounded-xl bg-blue-50 p-4">
          <p class="text-sm text-gray-600">Durak sayısı</p>
          <p class="text-2xl font-bold text-blue-700">{{ durakSayisi }}</p>
        </div>
        <div class="rounded-xl bg-blue-50 p-4">
          <p class="text-sm text-gray-600">Planlanan gün</p>
          <p class="text-2xl font-bold text-blue-700">{{ rota.days }}</p>
        </div>
      </div>

      <div class="mt-6 flex flex-wrap gap-2">
        <button v-for="(gun, index) in rota.itinerary" :key="gun.day" type="button"
          @click="aktifGun = index"
          :class="['rounded-lg px-4 py-2 font-semibold', aktifGun === index ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700']">
          Gün {{ gun.day }}
        </button>
      </div>

      <div v-if="seciliGun" class="mt-5 rounded-xl border p-5">
        <h3 class="text-xl font-bold">{{ seciliGun.day }}. Gün Rotası</h3>
        <p class="mt-2 text-sm text-gray-600">
          Ziyaret: {{ sureYaz(seciliGun.visit_minutes) }} · Yol: ~{{ sureYaz(seciliGun.travel_minutes) }} ·
          <strong>Toplam: {{ sureYaz(seciliGun.total_minutes) }}</strong> · Mesafe: {{ seciliGun.distance_km.toFixed(2) }} km
        </p>
        <p v-if="seciliGun.places.length === 0" class="mt-5 text-gray-500">
          Bu gün için koordinatı ve ziyaret süresi uygun yer bulunamadı.
        </p>
        <div v-for="yer in seciliGun.places" :key="yer.place_id" class="mt-4 rounded-lg bg-slate-50 p-4">
          <p class="font-semibold">{{ yer.order }}. {{ yer.name }}</p>
          <p class="mt-1 text-sm text-gray-600">{{ yer.category ?? "Kategori belirtilmedi" }} · {{ yer.visit_minutes }} dakika</p>
          <p v-if="yer.order > 1" class="mt-1 text-sm text-blue-700">
            Önceki duraktan: {{ yer.distance_from_previous_km }} km · ~{{ yer.travel_minutes }} dk
            {{ yer.distance_from_previous_km <= 1.5 ? "🚶 yürüyüş" : "🚇 toplu taşıma" }}
          </p>
          <p v-else class="mt-1 text-sm text-blue-700">Günün başlangıç noktası</p>
        </div>
        <ClientOnly>
          <RotaHaritasi v-if="seciliGun.places.length > 0" :key="`${cityId}-${seciliGun.day}-${kayitNo ?? 'yeni'}`" :places="seciliGun.places" />
        </ClientOnly>
      </div>

      <p class="mt-5 text-sm text-amber-700">
        Koordinatı eksik/geçersiz: {{ rota.excluded.missing_or_invalid_coordinates }} ·
        Ziyaret süresi eksik: {{ rota.excluded.missing_visit_duration }} ·
        Süreye sığmayan: {{ rota.excluded.not_fitting_in_days }}
      </p>
      <p class="mt-3 text-sm text-gray-500">{{ rota.warning }}</p>
    </div>
  </section>
</template>
