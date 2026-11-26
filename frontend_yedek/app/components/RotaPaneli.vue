
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
}

interface Gun {
  day: number;
  places: RotaYeri[];
  visit_minutes: number;
  distance_km: number;
  distance_before_2opt_km: number;
}

interface RotaCevabi {
  city: string;
  days: number;
  hours_per_day: number;
  total_distance_km: number;
  routed_places: number;
  itinerary: Gun[];
  excluded: {
    missing_or_invalid_coordinates: number;
    missing_visit_duration: number;
    not_fitting_in_days: number;
  };
  warning: string;
}

const props = defineProps<{
  cityId: number;
}>();

const gunSayisi = ref(3);
const gunlukSaat = ref(5);
const aktifGun = ref(0);

const rota = ref<RotaCevabi | null>(null);
const yukleniyor = ref(false);
const hata = ref("");

let istekNo = 0;

const seciliGun = computed(() =>
  rota.value?.itinerary[aktifGun.value] ?? null
);

async function rotaGetir() {
  const buIstek = ++istekNo;

  yukleniyor.value = true;
  hata.value = "";
  rota.value = null;
  aktifGun.value = 0;

  try {
    const params = new URLSearchParams({
      days: String(gunSayisi.value),
      hours_per_day: String(gunlukSaat.value)
    });

    const cevap = await fetch(
      `http://127.0.0.1:8001/destinations/${props.cityId}/route?${params}`
    );

    if (!cevap.ok) {
      throw new Error(`API hatası: ${cevap.status}`);
    }

    const sonuc: RotaCevabi = await cevap.json();

    if (buIstek !== istekNo) return;

    rota.value = sonuc;
  } catch (error) {
    if (buIstek !== istekNo) return;

    hata.value = "Rota oluşturulamadı. FastAPI bağlantısını kontrol et.";
    console.error(error);
  } finally {
    if (buIstek === istekNo) {
      yukleniyor.value = false;
    }
  }
}

// Şehir değişince eski rotayı temizle.
watch(
  () => props.cityId,
  () => {
    istekNo++;
    rota.value = null;
    hata.value = "";
    yukleniyor.value = false;
    aktifGun.value = 0;
  }
);
</script>

<template>
  <section class="mt-10 rounded-2xl bg-white p-6 shadow">
    <h2 class="text-2xl font-bold text-slate-800">
      🧭 Akıllı Rota Planlayıcı
    </h2>

    <p class="mt-2 text-gray-600">
      Gün sayısını ve günlük gezi süresini belirle.
      VoyageAI ziyaret sırasını hesaplasın.
    </p>

    <div class="mt-6 grid gap-6 md:grid-cols-2">
      <div>
        <label for="rota-gun" class="font-semibold">
          Gün sayısı: {{ gunSayisi }}
        </label>
        <input
          id="rota-gun"
          v-model.number="gunSayisi"
          type="range"
          min="1"
          max="7"
          class="mt-3 w-full accent-blue-600"
          @input="rota = null"
        />
      </div>

      <div>
        <label for="rota-saat" class="font-semibold">
          Günlük süre: {{ gunlukSaat }} saat
        </label>
        <input
          id="rota-saat"
          v-model.number="gunlukSaat"
          type="range"
          min="1"
          max="12"
          class="mt-3 w-full accent-blue-600"
          @input="rota = null"
        />
      </div>
    </div>

    <button
      type="button"
      :disabled="yukleniyor"
      @click="rotaGetir"
      class="mt-6 rounded-xl bg-blue-600 px-6 py-3
             font-semibold text-white hover:bg-blue-700
             disabled:opacity-50"
    >
      {{ yukleniyor ? "Hesaplanıyor..." : "🧭 Rotayı Oluştur" }}
    </button>

    <p v-if="hata" class="mt-4 text-red-600" role="alert">
      {{ hata }}
    </p>

    <div v-if="rota" class="mt-8">
      <div class="grid gap-3 md:grid-cols-3">
        <div class="rounded-xl bg-blue-50 p-4">
          <p class="text-sm text-gray-600">Şehir</p>
          <p class="font-bold text-blue-700">{{ rota.city }}</p>
        </div>

        <div class="rounded-xl bg-green-50 p-4">
          <p class="text-sm text-gray-600">Rotaya eklenen yer</p>
          <p class="text-2xl font-bold text-green-700">
            {{ rota.routed_places }}
          </p>
        </div>

        <div class="rounded-xl bg-purple-50 p-4">
          <p class="text-sm text-gray-600">
            Toplam kuş uçuşu mesafe
          </p>
          <p class="text-2xl font-bold text-purple-700">
            {{ rota.total_distance_km.toFixed(2) }} km
          </p>
        </div>
      </div>

      <div class="mt-6 flex flex-wrap gap-2">
        <button
          v-for="(gun, index) in rota.itinerary"
          :key="gun.day"
          type="button"
          @click="aktifGun = index"
          :class="[
            'rounded-lg px-4 py-2 font-semibold',
            aktifGun === index
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-700'
          ]"
        >
          Gün {{ gun.day }}
        </button>
      </div>

      <div v-if="seciliGun" class="mt-5 rounded-xl border p-5">
        <h3 class="text-xl font-bold">
          {{ seciliGun.day }}. Gün Rotası
        </h3>

        <p class="mt-2 text-sm text-gray-600">
          Ziyaret süresi: {{ seciliGun.visit_minutes }} dk
          · Mesafe: {{ seciliGun.distance_km.toFixed(2) }} km
        </p>

        <p
          v-if="seciliGun.places.length === 0"
          class="mt-5 text-gray-500"
        >
          Bu gün için doğrulanmış koordinatı olan uygun yer bulunamadı.
        </p>

        <div
          v-for="yer in seciliGun.places"
          :key="yer.place_id"
          class="mt-4 rounded-lg bg-slate-50 p-4"
        >
          <p class="font-semibold">
            {{ yer.order }}. {{ yer.name }}
          </p>

          <p class="mt-1 text-sm text-gray-600">
            {{ yer.category ?? "Kategori belirtilmedi" }}
            · {{ yer.visit_minutes }} dakika
          </p>

          <p class="mt-1 text-sm text-blue-700">
            Önceki duraktan: {{ yer.distance_from_previous_km }} km
          </p>
        </div>
        <ClientOnly>
  <RotaHaritasi
    v-if="seciliGun.places.length > 0"
    :key="`${cityId}-${seciliGun.day}`"
    :places="seciliGun.places"
  />
</ClientOnly>
      </div>

      <p class="mt-5 text-sm text-amber-700">
        Koordinatı eksik/geçersiz: {{ rota.excluded.missing_or_invalid_coordinates }}
        · Ziyaret süresi eksik: {{ rota.excluded.missing_visit_duration }}
        · Süreye sığmayan: {{ rota.excluded.not_fitting_in_days }}
      </p>

      <p class="mt-3 text-sm text-gray-500">
        {{ rota.warning }}
      </p>
    </div>
  </section>
</template>
