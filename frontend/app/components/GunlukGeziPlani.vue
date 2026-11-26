
<script setup lang="ts">
import { ref, computed, watch } from "vue";

interface Yer {
  id: number;
  name: string;
  category: string | null;
  visit_duration: number | null;
}

const props = defineProps<{
  cityName: string;
  places: Yer[];
}>();

const saat = ref(5);
const planOlusturuldu = ref(false);

const sureLimiti = computed(() => saat.value * 60);

const plan = computed(() => {
  if (!planOlusturuldu.value) return [];

  let toplam = 0;
  const secilenler: Yer[] = [];

  // Sadece ziyaret süresi bilinen yerleri kullan.
  for (const yer of props.places) {
    const sure = yer.visit_duration;

    if (sure == null || sure <= 0) continue;

    if (toplam + sure <= sureLimiti.value) {
      secilenler.push(yer);
      toplam += sure;
    }
  }

  return secilenler;
});

const toplamSure = computed(() =>
  plan.value.reduce(
    (toplam, yer) => toplam + (yer.visit_duration ?? 0),
    0
  )
);

function sureyiYazdir(dakika: number) {
  const saat = Math.floor(dakika / 60);
  const dakikaKalan = dakika % 60;

  if (saat === 0) return `${dakikaKalan} dakika`;
  if (dakikaKalan === 0) return `${saat} saat`;

  return `${saat} saat ${dakikaKalan} dakika`;
}

// Şehir veya yer listesi değişince eski planı temizle.
watch(
  () => [props.cityName, props.places],
  () => {
    planOlusturuldu.value = false;
  }
);
</script>

<template>
  <section class="mt-10 rounded-2xl bg-white p-6 shadow">

    <h2 class="text-2xl font-bold text-slate-800">
      🧳 Günlük Gezi Planı
    </h2>

    <p class="mt-2 text-gray-600">
      {{ cityName }} şehrinde gezmeye kaç saat ayıracaksın?
    </p>

    <div class="mt-6 max-w-lg">
      <div class="mb-3 flex justify-between">
        <label for="gezi-saati" class="font-semibold">
          Gezi süresi
        </label>

        <span class="font-bold text-blue-700">
          {{ saat }} saat
        </span>
      </div>

      <input
        id="gezi-saati"
        v-model.number="saat"
        type="range"
        min="1"
        max="12"
        step="1"
        class="w-full accent-blue-600"
        @input="planOlusturuldu = false"
      />
    </div>

    <button
      type="button"
      @click="planOlusturuldu = true"
      class="mt-6 rounded-xl bg-blue-600 px-6 py-3
             font-semibold text-white hover:bg-blue-700"
    >
      ✨ Gezi Planı Oluştur
    </button>

    <div v-if="planOlusturuldu" class="mt-8">

      <h3 class="mb-4 text-xl font-bold">
        {{ cityName }} için gezi planın
      </h3>

      <p v-if="plan.length === 0" class="text-gray-600">
        Seçilen süreye uygun gezilecek yer bulunamadı.
      </p>

      <div v-else class="space-y-3">
        <div
          v-for="(yer, index) in plan"
          :key="yer.id"
          class="flex items-center justify-between
                 rounded-xl border border-gray-200 p-4"
        >
          <div>
            <p class="font-semibold">
              {{ index + 1 }}. {{ yer.name }}
            </p>

            <p class="mt-1 text-sm text-gray-500">
              {{ yer.category ?? "Kategori belirtilmemiş" }}
            </p>
          </div>

          <span class="font-semibold text-blue-700">
            {{ sureyiYazdir(yer.visit_duration ?? 0) }}
          </span>
        </div>
      </div>

      <div
        v-if="plan.length > 0"
        class="mt-6 rounded-xl bg-blue-50 p-5"
      >
        <p class="text-sm text-gray-600">
          Toplam tahmini ziyaret süresi
        </p>

        <p class="mt-2 text-2xl font-bold text-blue-700">
          {{ sureyiYazdir(toplamSure) }}
        </p>

        <p class="mt-2 text-sm text-gray-600">
          Kalan süre:
          {{ sureyiYazdir(sureLimiti - toplamSure) }}
        </p>
      </div>

      <p class="mt-4 text-sm text-gray-500">
        Bu plan mevcut gezilecek yer listesinin sırasına göre
        hazırlanır. Ulaşım, sıra bekleme ve molalar henüz
        hesaba katılmamıştır. Ziyaret süreleri tahminidir.
      </p>

    </div>

  </section>
</template>
