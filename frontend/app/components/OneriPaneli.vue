
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
  <section class="b-bolum">
    <p class="v-ust-yazi">Tercihlerin</p>
    <h2 class="v-baslik">Sana uygun şehirleri bul</h2>
    <p class="b-aciklama">Seyahatinde nelere önem verdiğini belirle, VoyageAI tercihlerine uygun şehirleri önersin.</p>

    <div class="b-alanlar">
      <div>
        <label for="doga" class="b-etiket">🌿 Doğa <strong>{{ doga }}</strong></label>
        <input id="doga" v-model.number="doga" type="range" min="0" max="100" step="5" class="b-kaydirici" />
      </div>
      <div>
        <label for="yemek" class="b-etiket">🍽️ Yemek <strong>{{ yemek }}</strong></label>
        <input id="yemek" v-model.number="yemek" type="range" min="0" max="100" step="5" class="b-kaydirici" />
      </div>
      <div>
        <label for="tarih" class="b-etiket">🏛️ Tarih <strong>{{ tarih }}</strong></label>
        <input id="tarih" v-model.number="tarih" type="range" min="0" max="100" step="5" class="b-kaydirici" />
      </div>
      <div>
        <label for="gece" class="b-etiket">🌙 Gece hayatı <strong>{{ gece }}</strong></label>
        <input id="gece" v-model.number="gece" type="range" min="0" max="100" step="5" class="b-kaydirici" />
      </div>
    </div>

    <div class="b-butonlar">
      <button type="button" class="v-buton" :disabled="yukleniyor" @click="onerileriGetir">
        {{ yukleniyor ? "Öneriler hazırlanıyor..." : "Şehir öner" }}
      </button>
    </div>

    <p v-if="hata" class="b-hata" role="alert">{{ hata }}</p>

    <div v-if="sonucGoster" style="margin-top: 28px">
      <p class="v-ust-yazi">Sonuçlar</p>
      <h3 class="v-baslik" style="font-size: 22px">Sana önerilen şehirler</h3>

      <p v-if="oneriler.length === 0" class="b-not">
        Bu tercihlere uygun, yeterli kayıt içeren şehir bulunamadı.
      </p>

      <div class="oneri-izgara">
        <article v-for="(oneri, index) in oneriler" :key="`${oneri.ulke}-${oneri.sehir}`" class="oneri-kart v-kart">
          <p class="v-ust-yazi">{{ index + 1 }}. öneri</p>
          <h4>{{ oneri.sehir }}</h4>
          <p class="b-durak-alt">{{ oneri.ulke }}</p>
          <p class="oneri-puan">{{ oneri.puan.toFixed(2) }}</p>
          <p class="b-durak-alt">Kategori uyum puanı · {{ oneri.toplam_yer }} gezilecek yer</p>
          <button type="button" class="v-buton oneri-buton" @click="sehriKesfet(oneri)">Bu şehri keşfet</button>
        </article>
      </div>

      <p class="b-not">
        Not: Bu sonuçlar kayıtlı gezilecek yerlerin kategori dağılımına dayalı prototip önerilerdir;
        şehirlerin gerçek kalitesini ölçmez.
      </p>
    </div>
  </section>
</template>

<style scoped>
.oneri-izgara {
  display: grid;
  gap: 14px;
  margin-top: 18px;
}

@media (min-width: 768px) {
  .oneri-izgara { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (min-width: 1024px) {
  .oneri-izgara { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}

.oneri-kart {
  padding: 20px;
}

.oneri-kart h4 {
  margin: 6px 0 0;
  color: var(--v-ink);
  font-size: 20px;
  font-weight: 800;
}

.oneri-puan {
  margin: 14px 0 0;
  color: var(--v-lilac-deep);
  font-size: 26px;
  font-weight: 800;
}

.oneri-buton {
  width: 100%;
  margin-top: 16px;
}
</style>

