
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
  <section class="b-bolum">
    <p class="v-ust-yazi">Hızlı plan</p>
    <h2 class="v-baslik">Günlük gezi planı</h2>
    <p class="b-aciklama">{{ cityName }} şehrinde gezmeye kaç saat ayıracaksın?</p>

    <div class="b-alanlar">
      <div>
        <label for="gezi-saati" class="b-etiket">Gezi süresi <strong>{{ saat }} saat</strong></label>
        <input id="gezi-saati" v-model.number="saat" type="range" min="1" max="12" step="1"
          class="b-kaydirici" @input="planOlusturuldu = false" />
      </div>
    </div>

    <div class="b-butonlar">
      <button type="button" class="v-buton" @click="planOlusturuldu = true">Gezi planı oluştur</button>
    </div>

    <div v-if="planOlusturuldu">
      <p v-if="plan.length === 0" class="b-not">Seçilen süreye uygun gezilecek yer bulunamadı.</p>

      <template v-else>
        <div v-for="(yer, index) in plan" :key="yer.id" class="b-durak">
          <span class="b-durak-no">{{ index + 1 }}</span>
          <div>
            <p class="b-durak-ad">{{ yer.name }}</p>
            <p class="b-durak-alt">{{ yer.category ?? "Kategori belirtilmemiş" }}</p>
          </div>
          <span class="b-durak-sure">{{ sureyiYazdir(yer.visit_duration ?? 0) }}</span>
        </div>

        <div class="b-ozet" style="grid-template-columns: repeat(2, minmax(0, 1fr))">
          <div class="b-ozet-kart">
            <span>Toplam ziyaret süresi</span>
            <strong>{{ sureyiYazdir(toplamSure) }}</strong>
          </div>
          <div class="b-ozet-kart">
            <span>Kalan süre</span>
            <strong>{{ sureyiYazdir(sureLimiti - toplamSure) }}</strong>
          </div>
        </div>
      </template>

      <p class="b-not">
        Bu hızlı plan yer listesinin sırasına göre hazırlanır; yol süresi dahil değildir.
        Yakın yerleri gruplayan ve yol süresini hesaplayan plan için aşağıdaki rota planlayıcıyı kullan.
      </p>
    </div>
  </section>
</template>
