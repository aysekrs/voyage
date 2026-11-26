
<script setup lang="ts">
import { ref } from "vue";

interface Oneri {
  sehir: string;
  ulke: string;
  puan: number;
  toplam_yer: number;
}

interface OneriCevabi {
  tercihler: Record<string, number>;
  oneriler: Oneri[];
  aciklama: string;
}

const API_URL = "http://127.0.0.1:8000";
const emit = defineEmits<{
  (e: "sehirKesfet", ulke: string, sehir: string): void;
}>();

function sehriKesfet(oneri: Oneri) {
  emit("sehirKesfet", oneri.ulke, oneri.sehir);
}

const doga = ref(30);
const yemek = ref(20);
const tarih = ref(40);
const gece = ref(10);

const oneriler = ref<Oneri[]>([]);
const yukleniyor = ref(false);
const hata = ref("");
const sonucGoster = ref(false);

async function onerileriGetir() {
  hata.value = "";
  oneriler.value = [];
  sonucGoster.value = false;

  const toplam = doga.value + yemek.value
    + tarih.value + gece.value;

  if (toplam === 0) {
    hata.value = "En az bir tercihi 0'dan büyük seçmelisin.";
    return;
  }

  yukleniyor.value = true;

  try {
    const params = new URLSearchParams({
      doga: String(doga.value),
      yemek: String(yemek.value),
      tarih: String(tarih.value),
      gece: String(gece.value)
    });

    const response = await fetch(
      `${API_URL}/recommendations?${params.toString()}`
    );

    if (!response.ok) {
      throw new Error(`API hatası: ${response.status}`);
    }

    const data: OneriCevabi = await response.json();

    oneriler.value = data.oneriler;
    sonucGoster.value = true;
  } catch (error) {
    hata.value =
      "Öneriler yüklenemedi. FastAPI bağlantısını kontrol et.";
    console.error(error);
  } finally {
    yukleniyor.value = false;
  }
}
</script>

<template>
  <section class="mt-10 rounded-2xl bg-white p-6 shadow">
    <h2 class="text-2xl font-bold text-slate-800">
      ✨ Sana Uygun Şehirleri Bul
    </h2>

    <p class="mt-2 text-gray-600">
      Seyahatinde nelere önem verdiğini belirle.
      VoyageAI tercihlerine uygun şehirleri önersin!
    </p>

    <div class="mt-8 grid gap-6 md:grid-cols-2">

      <div>
        <div class="mb-2 flex justify-between">
          <label for="doga">🌿 Doğa</label>
          <span class="font-bold text-green-700">
            {{ doga }}
          </span>
        </div>

        <input
          id="doga"
          v-model.number="doga"
          type="range"
          min="0"
          max="100"
          step="5"
          class="w-full accent-green-600"
        />
      </div>

      <div>
        <div class="mb-2 flex justify-between">
          <label for="yemek">🍽️ Yemek</label>
          <span class="font-bold text-orange-600">
            {{ yemek }}
          </span>
        </div>

        <input
          id="yemek"
          v-model.number="yemek"
          type="range"
          min="0"
          max="100"
          step="5"
          class="w-full accent-orange-500"
        />
      </div>

      <div>
        <div class="mb-2 flex justify-between">
          <label for="tarih">🏛️ Tarih</label>
          <span class="font-bold text-blue-700">
            {{ tarih }}
          </span>
        </div>

        <input
          id="tarih"
          v-model.number="tarih"
          type="range"
          min="0"
          max="100"
          step="5"
          class="w-full accent-blue-600"
        />
      </div>

      <div>
        <div class="mb-2 flex justify-between">
          <label for="gece">🌙 Gece hayatı</label>
          <span class="font-bold text-purple-700">
            {{ gece }}
          </span>
        </div>

        <input
          id="gece"
          v-model.number="gece"
          type="range"
          min="0"
          max="100"
          step="5"
          class="w-full accent-purple-600"
        />
      </div>

    </div>

    <button
      type="button"
      @click="onerileriGetir"
      :disabled="yukleniyor"
      class="mt-8 rounded-xl bg-blue-600 px-6 py-3
             font-semibold text-white
             hover:bg-blue-700
             disabled:cursor-not-allowed
             disabled:opacity-50"
    >
      {{ yukleniyor ? "Öneriler hazırlanıyor..." : "Şehir Öner!" }}
    </button>

    <p
      v-if="hata"
      class="mt-4 text-red-600"
      role="alert"
    >
      {{ hata }}
    </p>

    <div v-if="sonucGoster" class="mt-10">
      <h3 class="mb-5 text-xl font-bold">
        🌍 Sana Önerilen Şehirler
      </h3>

      <p
        v-if="oneriler.length === 0"
        class="text-gray-600"
      >
        Bu tercihlere uygun, yeterli kayıt içeren şehir bulunamadı.
      </p>

      <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <article
          v-for="(oneri, index) in oneriler"
          :key="`${oneri.ulke}-${oneri.sehir}`"
          class="rounded-xl border border-gray-200 p-5"
        >
          <p class="text-sm font-semibold text-blue-600">
            {{ index + 1 }}. Öneri
          </p>

          <h4 class="mt-2 text-xl font-bold">
            {{ oneri.sehir }}
          </h4>

          <p class="mt-1 text-gray-600">
            {{ oneri.ulke }}
          </p>

          <p class="mt-4 text-2xl font-bold text-green-700">
            {{ oneri.puan.toFixed(2) }}
          </p>

          <p class="text-sm text-gray-500">
            Kategori uyum puanı
          </p>

          <p class="mt-3 text-sm text-gray-600">
            Kayıtlı gezilecek yer: {{ oneri.toplam_yer }}
          </p>
          <button
  type="button"
  @click="sehriKesfet(oneri)"
  class="mt-5 w-full rounded-lg bg-blue-600 px-4 py-3
         font-semibold text-white transition hover:bg-blue-700"
>
  📍 Bu Şehri Keşfet
</button>
        </article>
      </div>

      <p class="mt-5 text-sm text-gray-500">
        Not: Bu sonuçlar kayıtlı gezilecek yerlerin
        kategori dağılımına dayalı prototip önerilerdir.
        Şehirlerin gerçek kalitesini ölçmez.
      </p>
    </div>
  </section>
</template>

