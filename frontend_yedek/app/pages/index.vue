
<script setup lang="ts">
import { ref, computed, onMounted,nextTick} from "vue";

interface Sehir {
  id: number;
  name: string;
  country: string;
}

interface Yer {
  id: number;
  name: string;
  category: string | null;
  latitude: number | null;
  longitude: number | null;
  visit_duration: number | null;
  average_price: number | null;
}

const API_URL = "http://127.0.0.1:8000";

const sehirler = ref<Sehir[]>([]);
const secilenUlke = ref("");
const secilenSehir = ref("");
const yerler = ref<Yer[]>([]);
const secilenKategori = ref("hepsi");
const secilenYerId = ref<number | null>(null);
const haritadaOlanYerler = ref<number[]>([]);

const kategoriler = [
  { deger: "hepsi", ad: "Tümü" },
  { deger: "tarih", ad: "??�?️ Tarih" },
  { deger: "do�?a", ad: "???� Do�?a" },
  { deger: "yemek", ad: "??��️ Yemek" },
  { deger: "gece_hayati", ad: "???? Gece Hayatı" }
];

const filtrelenmisYerler = computed(() => {
  if (secilenKategori.value === "hepsi") {
    return yerler.value;
  }

  return yerler.value.filter(
    yer => yer.category === secilenKategori.value
  );
});

const toplamZiyaretSuresi = computed(() => {
  return filtrelenmisYerler.value.reduce(
    (toplam, yer) => toplam + (yer.visit_duration ?? 0),
    0
  );
});

const eksikSureSayisi = computed(() =>
  filtrelenmisYerler.value.filter(
    yer => yer.visit_duration == null
  ).length
);

function sureyiYazdir(dakika: number) {
  const saat = Math.floor(dakika / 60);
  const kalanDakika = dakika % 60;

  if (saat === 0) return `${kalanDakika} dakika`;
  if (kalanDakika === 0) return `${saat} saat`;

  return `${saat} saat ${kalanDakika} dakika`;
}

const yukleniyor = ref(true);
const yerlerYukleniyor = ref(false);
const hata = ref("");

const ulkeler = computed(() => {
  return [...new Set(sehirler.value.map(s => s.country))]
    .sort((a, b) => a.localeCompare(b, "tr"));
});

const filtreliSehirler = computed(() => {
  return sehirler.value.filter(
    s => s.country === secilenUlke.value
  );
});

onMounted(async () => {
  try {
    const response = await fetch(`${API_URL}/destinations`);

    if (!response.ok) {
      throw new Error("Şehirler alınamadı");
    }

    sehirler.value = await response.json();
  } catch {
    hata.value = "Şehirler yüklenemedi. Backend ba�?lantısını kontrol et.";
  } finally {
    yukleniyor.value = false;
  }
});

function ulkeDegisti() {
  secilenSehir.value = "";
  yerler.value = [];
  hata.value = "";
}

async function sehirDegisti() {
  haritadaOlanYerler.value = [];
  secilenYerId.value = null;
  secilenKategori.value = "hepsi";
  yerler.value = [];
  hata.value = "";

  if (!secilenSehir.value) return;

  yerlerYukleniyor.value = true;

  try {
    const response = await fetch(
      `${API_URL}/destinations/${secilenSehir.value}/places`
    );

    if (!response.ok) {
      throw new Error("Gezilecek yerler alınamadı");
    }

    yerler.value = await response.json();
  } catch {
    hata.value = "Gezilecek yerler yüklenemedi.";
  } finally {
    yerlerYukleniyor.value = false;
  }
}

const aktifSehir = computed(() =>
  sehirler.value.find(
    s => String(s.id) === secilenSehir.value
  )
);

async function onerilenSehriAc(ulke: string, sehirAdi: string) {
  const bulunanSehir = sehirler.value.find(
    s => s.country === ulke && s.name === sehirAdi
  );

  if (!bulunanSehir) {
    hata.value = `${sehirAdi} �?ehir listesinde bulunamadı.`;
    return;
  }

  secilenUlke.value = bulunanSehir.country;
  secilenSehir.value = String(bulunanSehir.id);

  await sehirDegisti();

  await nextTick();

  document.getElementById("gezilecek-yerler")
    ?.scrollIntoView({
      behavior: "smooth",
      block: "start"
    });
}

</script>

<template>
  <main class="min-h-screen bg-slate-100 p-6 text-slate-900">
    <div class="mx-auto max-w-6xl">

      <header class="mb-10">
        <h1 class="text-4xl font-bold text-blue-700">
          ???� VoyageAI
        </h1>

        <p class="mt-3 text-gray-600">
          Dünyayı ke�?fet, seyahatini planla!
        </p>
      </header>

      <section class="rounded-2xl bg-white p-6 shadow">
        <h2 class="mb-6 text-2xl font-semibold">
          Nereye gitmek istersin?
        </h2>

        <div class="grid gap-5 md:grid-cols-2">

          <div>
            <label for="ulke" class="mb-2 block font-medium">
              �?lke seç
            </label>

            <select
              id="ulke"
              v-model="secilenUlke"
              @change="ulkeDegisti"
              class="w-full rounded-lg border border-gray-300 p-3"
            >
              <option value="">�?lke seçiniz</option>

              <option
                v-for="ulke in ulkeler"
                :key="ulke"
                :value="ulke"
              >
                {{ ulke }}
              </option>
            </select>
          </div>

          <div>
            <label for="sehir" class="mb-2 block font-medium">
              Şehir seç
            </label>

            <select
              id="sehir"
              v-model="secilenSehir"
              @change="sehirDegisti"
              :disabled="!secilenUlke"
              class="w-full rounded-lg border border-gray-300 p-3 disabled:bg-gray-100"
            >
              <option value="">Şehir seçiniz</option>

              <option
                v-for="sehir in filtreliSehirler"
                :key="sehir.id"
                :value="String(sehir.id)"
              >
                {{ sehir.name }}
              </option>
            </select>
          </div>

        </div>
      </section>

      <p v-if="yukleniyor" class="mt-6">
        Şehirler yükleniyor...
      </p>

      <p v-if="hata" class="mt-6 text-red-600">
        {{ hata }}
      </p>

      <section
  v-if="aktifSehir"
  id="gezilecek-yerler"
  class="mt-10 scroll-mt-6"
>
        <h2 class="mb-5 text-2xl font-bold">
          {{ aktifSehir.name }} Gezilecek Yerler
        </h2>
        
<div class="mb-6 rounded-xl bg-white p-5 shadow-sm">

  <label
    for="kategori"
    class="mb-2 block font-semibold text-gray-700"
  >
    Gezilecek yer kategorisi
  </label>

  <select
    id="kategori"
    v-model="secilenKategori"
    class="w-full rounded-lg border border-gray-300 p-3 md:w-80"
  >
    <option
      v-for="kategori in kategoriler"
      :key="kategori.deger"
      :value="kategori.deger"
    >
      {{ kategori.ad }}
    </option>
  </select>

  <div class="mt-5 grid gap-3 md:grid-cols-2">

    <div class="rounded-lg bg-blue-50 p-4">
      <p class="text-sm text-gray-600">
        Görüntülenen gezilecek yer
      </p>

      <p class="mt-1 text-2xl font-bold text-blue-700">
        {{ filtrelenmisYerler.length }}
      </p>
    </div>

    <div class="rounded-lg bg-green-50 p-4">
      <p class="text-sm text-gray-600">
        Toplam tahmini ziyaret süresi
      </p>

      <p class="mt-1 text-2xl font-bold text-green-700">
        {{ sureyiYazdir(toplamZiyaretSuresi) }}
      </p>

      <p
        v-if="eksikSureSayisi > 0"
        class="mt-1 text-xs text-gray-500"
      >
        {{ eksikSureSayisi }} yerin süresi bilinmiyor.
      </p>
    </div>

  </div>

  <p class="mt-3 text-xs text-gray-500">
    Süreler tahminidir; ula�?ım, sıra bekleme ve mola süreleri
    hesaplamaya dahil de�?ildir.
  </p>

</div>


        <p v-if="yerlerYukleniyor">
          Gezilecek yerler yükleniyor...
        </p>

        <p
          v-else-if="!hata && filtrelenmisYerler.length === 0"
          class="text-gray-600"
        >
          Bu kategori için gezilecek yer bulunamadı.
        </p>

        <div class="grid gap-5 md:grid-cols-3">
          <article
            v-for="yer in filtrelenmisYerler"
            :key="yer.id"
            class="rounded-xl bg-white p-5 shadow transition hover:shadow-lg"
          >
            <h3 class="text-lg font-bold text-blue-700">
              {{ yer.name }}
            </h3>

            <p class="mt-2 text-sm text-gray-600">
              Kategori: {{ yer.category ?? "Belirtilmedi" }}
            </p>

            <p class="mt-3 text-sm">
              Ziyaret süresi:
              {{
                yer.visit_duration === null
                  ? "Henüz bilinmiyor"
                  : `${yer.visit_duration} dakika`
              }}
            </p>

            <p class="mt-2 text-sm">
              Ortalama ücret:
              {{
                yer.average_price === null
                  ? "Henüz bilinmiyor"
                  : yer.average_price
              }}
            </p>
            <button
            v-if="haritadaOlanYerler.includes(yer.id)"
  type="button"
  @click="secilenYerId = yer.id"
  class="mt-5 rounded-lg bg-blue-600 px-4 py-2
         text-sm font-semibold text-white hover:bg-blue-700"
>
  ???� Haritada Göster
</button>
<p
  v-if="!haritadaOlanYerler.includes(yer.id)"
  class="mt-5 text-sm text-gray-400"
>
  ???� Konum bilgisi henüz mevcut de�?il.
</p>
          </article>
        </div>
      </section>
     <SehirHaritasi
  v-if="aktifSehir"
  :city-id="aktifSehir.id"
  :selected-place-id="secilenYerId"
  @konumlar-yuklendi="haritadaOlanYerler = $event"
/>
<GunlukGeziPlani
  v-if="aktifSehir && !yerlerYukleniyor && !hata"
  :key="aktifSehir.id"
  :city-name="aktifSehir.name"
  :places="yerler"
/>
<RotaPaneli
  v-if="aktifSehir"
  :key="aktifSehir.id"
  :city-id="aktifSehir.id"
/>
<OneriPaneli @sehir-kesfet="onerilenSehriAc" />
    </div>
  </main>
</template>




