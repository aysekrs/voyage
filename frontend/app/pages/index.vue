
<script setup lang="ts">
import { ref, computed, onMounted,nextTick} from "vue";
import SeyahatOlustur from '~/components/SeyahatOlustur.vue'
import SeyahatListesi from '~/components/SeyahatListesi.vue'

const route = useRoute()
const seyahatFormuAcik = ref(false)
const girisYapildi = ref(false)
const oturumKontrolEdiliyor = ref(false)

async function seyahatOlusturAc() {
  oturumKontrolEdiliyor.value = true

  try {
    await $fetch('/api/ben')

    seyahatFormuAcik.value = true
    await nextTick()

    document.getElementById('seyahat-olustur')
      ?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  } catch {
    await navigateTo('/login?redirect=%2F%3FseyahatOlustur%3D1')
  } finally {
    oturumKontrolEdiliyor.value = false
  }
}

onMounted(() => {
  $fetch('/api/ben')
    .then(() => { girisYapildi.value = true })
    .catch(() => { girisYapildi.value = false })

  if (route.query.seyahatOlustur === '1') {
    seyahatOlusturAc()
  }
})


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
  { deger: "tarih", ad: "🏛️ Tarih" },
  { deger: "doğa", ad: "🌿 Doğa" },
  { deger: "yemek", ad: "🍽️ Yemek" },
  { deger: "gece_hayati", ad: "🌙 Gece Hayatı" }
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
    hata.value = "Şehirler yüklenemedi. Backend bağlantısını kontrol et.";
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
    hata.value = `${sehirAdi} şehir listesinde bulunamadı.`;
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
<main class="min-h-screen p-4 text-slate-900 md:p-6">
  <div class="mx-auto max-w-6xl">

  <!-- Üst bar -->
  <nav class="ana-nav">
    <NuxtLink to="/" class="ana-marka">
      <span class="marka-yildiz" aria-hidden="true">✦</span>
      Voyage<em>AI</em>
    </NuxtLink>

    <NuxtLink to="/login" class="nav-buton">
      {{ girisYapildi ? 'Hesabım' : 'Giriş yap' }}
    </NuxtLink>
  </nav>

  <!-- Karşılama alanı -->
  <header class="ana-banner">
    <div class="banner-yazi">
      <span class="banner-etiket">VOYAGEAI / SEYAHAT PLANLAYICI</span>
      <h1>Dünyayı keşfet, <em>seyahatini planla.</em></h1>
      <p>
        Bütçeni ve ilgi alanlarını söyle; sana uygun şehirleri, uçuşları,
        otelleri ve gün gün rotanı birlikte çıkaralım.
      </p>

      <button
        type="button"
        :disabled="oturumKontrolEdiliyor"
        class="banner-buton"
        @click="seyahatOlusturAc"
      >
        {{ oturumKontrolEdiliyor ? 'Kontrol ediliyor…' : '✈  Seyahat oluştur' }}
      </button>
    </div>

    <div class="banner-sanat" aria-hidden="true">
      <span class="sanat-gunes"></span>
      <span class="sanat-ucak">✈</span>
      <span class="sanat-yol"></span>
      <span class="sanat-tepe tepe-arka"></span>
      <span class="sanat-tepe tepe-on"></span>
    </div>
  </header>

<div
  v-if="seyahatFormuAcik"
  id="seyahat-olustur"
  class="mb-8 scroll-mt-6"
>
  <SeyahatOlustur />
</div>

<div v-if="seyahatFormuAcik" class="mb-8">
  <SeyahatListesi />
</div>

      <section class="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm md:p-8">
        <h2 class="mb-6 text-2xl font-semibold">
          Nereye gitmek istersin?
        </h2>

        <div class="grid gap-5 md:grid-cols-2">

          <div>
            <label for="ulke" class="mb-2 block font-medium">
              Ülke seç
            </label>

            <select
              id="ulke"
              v-model="secilenUlke"
              @change="ulkeDegisti"
              class="w-full rounded-lg border border-gray-300 p-3"
            >
              <option value="">Ülke seçiniz</option>

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
    Süreler tahminidir; ulaşım, sıra bekleme ve mola süreleri
    hesaplamaya dahil değildir.
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
  📍 Haritada Göster
</button>
<p
  v-if="!haritadaOlanYerler.includes(yer.id)"
  class="mt-5 text-sm text-gray-400"
>
  📍 Konum bilgisi henüz mevcut değil.
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

<style scoped>
.ana-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
  padding: 6px 4px;
}

.ana-marka {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--v-ink);
  font-family: var(--v-font-accent);
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.8px;
  text-decoration: none;
}

.ana-marka em {
  color: var(--v-lilac-deep);
  font-style: italic;
  font-weight: 400;
}

.marka-yildiz {
  color: var(--v-lilac);
  font-family: var(--v-font);
  font-size: 18px;
}

.nav-buton {
  padding: 9px 18px;
  border: 1px solid var(--v-line);
  border-radius: 12px;
  background: white;
  color: var(--v-muted);
  font-size: 14px;
  font-weight: 750;
  text-decoration: none;
  transition: border-color 0.2s, color 0.2s;
}

.nav-buton:hover {
  border-color: var(--v-lilac);
  color: var(--v-lilac-deep);
}

.ana-banner {
  position: relative;
  display: flex;
  align-items: center;
  min-height: 300px;
  margin-bottom: 32px;
  padding: 48px clamp(24px, 5vw, 72px);
  overflow: hidden;
  border-radius: 28px;
  background: var(--v-gradient-soft);
}

.banner-yazi {
  position: relative;
  z-index: 2;
  max-width: 620px;
}

.banner-etiket {
  color: #677fae;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 2px;
}

.banner-yazi h1 {
  margin: 16px 0 14px;
  color: var(--v-ink);
  font-size: clamp(32px, 4.4vw, 54px);
  font-weight: 750;
  letter-spacing: -1.6px;
  line-height: 1.1;
}

.banner-yazi h1 em {
  color: var(--v-lilac-deep);
  font-family: var(--v-font-accent);
  font-weight: 400;
}

.banner-yazi p {
  max-width: 520px;
  margin: 0 0 26px;
  color: #63708a;
  font-size: 15px;
  line-height: 1.75;
}

.banner-buton {
  padding: 14px 26px;
  border: 0;
  border-radius: 14px;
  background: var(--v-gradient-button);
  box-shadow: 0 12px 28px rgba(133, 114, 183, 0.25);
  color: white;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.banner-buton:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 16px 32px rgba(133, 114, 183, 0.32);
}

.banner-buton:disabled {
  cursor: default;
  opacity: 0.7;
}

.banner-sanat {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 40%;
  height: 100%;
  overflow: hidden;
  pointer-events: none;
}

.sanat-gunes {
  position: absolute;
  top: 40px;
  right: 24%;
  width: 130px;
  height: 130px;
  border-radius: 50%;
  background: #f9cfdb;
}

.sanat-ucak {
  position: absolute;
  top: 58px;
  right: 40%;
  color: #7c86bb;
  font-size: 54px;
  transform: rotate(-18deg);
}

.sanat-yol {
  position: absolute;
  top: 135px;
  right: 48%;
  width: 110px;
  height: 64px;
  border-bottom: 2px dashed #a9a1d4;
  border-radius: 50%;
  transform: rotate(20deg);
}

.sanat-tepe {
  position: absolute;
  width: 120%;
  height: 180px;
  border-radius: 50% 50% 0 0;
}

.tepe-arka {
  right: -20%;
  bottom: -95px;
  transform: rotate(-12deg);
  background: #c3b7e7;
}

.tepe-on {
  right: -35%;
  bottom: -115px;
  transform: rotate(12deg);
  background: #a8bee8;
}

@media (max-width: 760px) {
  .banner-sanat {
    opacity: 0.35;
    width: 70%;
  }
}
</style>
