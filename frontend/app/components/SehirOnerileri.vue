<script setup lang="ts">
// 5. Hafta: Sonuç ekranı. Tüm aday şehirlerin maliyeti ve puanı.
import { computed, onMounted, ref } from 'vue'

interface Oneri {
  id: number
  destination_id: number
  city: string
  country: string
  flight_cost: number | string
  accommodation_cost: number | string
  food_cost: number | string
  activity_cost: number | string
  local_transport_cost: number | string
  total_cost: number | string
  remaining_budget: number | string
  preference_score: number | string
  budget_fit_score: number | string
  overall_score: number | string
  is_selected: boolean
}

const props = defineProps<{ tripId: number; isOwner: boolean }>()
const emit = defineEmits<{ (e: 'secildi', destinationId: number): void }>()

const oneriler = ref<Oneri[]>([])
const yukleniyor = ref(false)
const hesaplaniyor = ref(false)
const secilenId = ref<number | null>(null)
const hata = ref('')
const hepsiniGoster = ref(false)

const ILK_GOSTERILEN = 6

const PARCALAR = [
  { anahtar: 'flight_cost', ad: 'Uçuş', renk: '#8fa9dc' },
  { anahtar: 'accommodation_cost', ad: 'Konaklama', renk: '#b7a6e0' },
  { anahtar: 'food_cost', ad: 'Yemek', renk: '#eeb3c6' },
  { anahtar: 'activity_cost', ad: 'Aktivite', renk: '#93cbbd' },
  { anahtar: 'local_transport_cost', ad: 'Şehir içi', renk: '#efc98f' }
] as const

const gorunenler = computed(() =>
  hepsiniGoster.value ? oneriler.value : oneriler.value.slice(0, ILK_GOSTERILEN)
)

function tl(deger: number | string) {
  return new Intl.NumberFormat('tr-TR', {
    style: 'currency',
    currency: 'TRY',
    maximumFractionDigits: 0
  }).format(Number(deger))
}

function yuzde(parca: number | string, toplam: number | string) {
  const t = Number(toplam)
  return t > 0 ? (Number(parca) / t) * 100 : 0
}

async function istek(url: string, method: 'GET' | 'POST') {
  const response = await fetch(url, { method, credentials: 'include' })
  const veri = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(veri?.message || `İstek başarısız (${response.status}).`)
  }
  return veri
}

async function getir() {
  yukleniyor.value = true
  hata.value = ''
  try {
    const veri = await istek(`/api/trips/${props.tripId}/options`, 'GET')
    oneriler.value = veri.options ?? []
  } catch (e) {
    hata.value = e instanceof Error ? e.message : 'Bir hata oluştu.'
  } finally {
    yukleniyor.value = false
  }
}

async function hesapla() {
  hesaplaniyor.value = true
  hata.value = ''
  try {
    const veri = await istek(`/api/trips/${props.tripId}/options`, 'POST')
    oneriler.value = veri.options ?? []
    hepsiniGoster.value = false
  } catch (e) {
    hata.value = e instanceof Error ? e.message : 'Bir hata oluştu.'
  } finally {
    hesaplaniyor.value = false
  }
}

async function sec(oneri: Oneri) {
  secilenId.value = oneri.id
  hata.value = ''
  try {
    await istek(`/api/trips/${props.tripId}/options/${oneri.id}/select`, 'POST')
    oneriler.value = oneriler.value.map(o => ({ ...o, is_selected: o.id === oneri.id }))
    emit('secildi', oneri.destination_id)
  } catch (e) {
    hata.value = e instanceof Error ? e.message : 'Şehir seçilemedi.'
  } finally {
    secilenId.value = null
  }
}

onMounted(getir)
</script>

<template>
  <div class="oneriler">
    <div class="ust-bar">
      <p v-if="oneriler.length" class="aciklama">
        {{ oneriler.length }} şehir genel puana göre sıralandı.
        Genel puan = %60 ilgi alanı uyumu + %40 bütçe uyumu.
      </p>
      <p v-else-if="!yukleniyor" class="aciklama">
        Henüz öneri hesaplanmadı. Bütçene ve ilgi alanlarına göre
        tüm şehirleri hesaplamak için butona bas.
      </p>

      <button
        v-if="isOwner"
        type="button"
        class="hesapla-buton"
        :disabled="hesaplaniyor"
        @click="hesapla"
      >
        {{ hesaplaniyor ? 'Hesaplanıyor…' : oneriler.length ? 'Yeniden hesapla' : 'Önerileri hesapla' }}
      </button>
    </div>

    <div v-if="hata" class="durum hata">{{ hata }}</div>
    <div v-if="yukleniyor" class="durum">Öneriler yükleniyor…</div>

    <div v-if="oneriler.length" class="lejant" aria-label="Maliyet renkleri">
      <span v-for="p in PARCALAR" :key="p.anahtar">
        <i :style="{ background: p.renk }"></i>{{ p.ad }}
      </span>
    </div>

    <div class="kartlar">
      <article
        v-for="(oneri, sira) in gorunenler"
        :key="oneri.id"
        class="kart"
        :class="{ secili: oneri.is_selected }"
      >
        <header class="kart-baslik">
          <div>
            <span class="sira">#{{ sira + 1 }}</span>
            <h4>{{ oneri.city }}</h4>
            <span class="ulke">{{ oneri.country }}</span>
          </div>
          <div class="genel-puan" :title="'Genel puan'">
            <strong>{{ Math.round(Number(oneri.overall_score)) }}</strong>
            <span>puan</span>
          </div>
        </header>

        <div class="rakamlar">
          <div>
            <span>Toplam fiyat</span>
            <strong>{{ tl(oneri.total_cost) }}</strong>
          </div>
          <div>
            <span>Kalan bütçe</span>
            <strong :class="{ eksi: Number(oneri.remaining_budget) < 0 }">
              {{ tl(oneri.remaining_budget) }}
            </strong>
          </div>
          <div>
            <span>İlgi uyumu</span>
            <strong>%{{ Math.round(Number(oneri.preference_score)) }}</strong>
          </div>
          <div>
            <span>Bütçe uyumu</span>
            <strong>%{{ Math.round(Number(oneri.budget_fit_score)) }}</strong>
          </div>
        </div>

        <div class="grafik" role="img" :aria-label="`${oneri.city} maliyet dağılımı`">
          <span
            v-for="p in PARCALAR"
            :key="p.anahtar"
            :style="{
              width: yuzde(oneri[p.anahtar], oneri.total_cost) + '%',
              background: p.renk
            }"
            :title="`${p.ad}: ${tl(oneri[p.anahtar])}`"
          ></span>
        </div>

        <ul class="dokum">
          <li v-for="p in PARCALAR" :key="p.anahtar">
            <i :style="{ background: p.renk }"></i>
            <span>{{ p.ad }}</span>
            <strong>{{ tl(oneri[p.anahtar]) }}</strong>
          </li>
        </ul>

        <button
          v-if="isOwner"
          type="button"
          class="sec-buton"
          :disabled="oneri.is_selected || secilenId !== null"
          @click="sec(oneri)"
        >
          {{ oneri.is_selected ? '✓ Seçildi' : secilenId === oneri.id ? 'Seçiliyor…' : 'Bu şehri seç' }}
        </button>
      </article>
    </div>

    <button
      v-if="oneriler.length > ILK_GOSTERILEN"
      type="button"
      class="hepsi-buton"
      @click="hepsiniGoster = !hepsiniGoster"
    >
      {{ hepsiniGoster ? 'Daha az göster' : `Tüm şehirleri göster (${oneriler.length})` }}
    </button>
  </div>
</template>

<style scoped>
.oneriler {
  display: grid;
  gap: 16px;
  color: #293042;
}

.ust-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.aciklama {
  margin: 0;
  color: #778197;
  font-size: 14px;
}

.hesapla-buton,
.sec-buton,
.hepsi-buton {
  border: 0;
  border-radius: 12px;
  font: inherit;
  font-weight: 750;
  cursor: pointer;
}

.hesapla-buton {
  padding: 10px 18px;
  background: #8e89c4;
  color: white;
}

.hesapla-buton:disabled,
.sec-buton:disabled {
  cursor: default;
  opacity: 0.7;
}

.durum {
  padding: 12px 14px;
  border-radius: 12px;
  background: #f1f4fb;
  color: #687590;
  font-size: 14px;
}

.durum.hata {
  background: #fff1f4;
  color: #b45f7b;
}

.lejant {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  color: #778197;
  font-size: 13px;
}

.lejant span,
.dokum li {
  display: flex;
  align-items: center;
  gap: 6px;
}

.lejant i,
.dokum i {
  width: 10px;
  height: 10px;
  flex: none;
  border-radius: 3px;
}

.kartlar {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 14px;
}

.kart {
  display: grid;
  gap: 14px;
  padding: 18px;
  border: 1px solid #e5e7f0;
  border-radius: 18px;
  background: white;
}

.kart.secili {
  border-color: #a999d5;
  box-shadow: 0 0 0 3px #eee8fa;
}

.kart-baslik {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.sira {
  color: #8e89c4;
  font-size: 12px;
  font-weight: 800;
}

.kart-baslik h4 {
  margin: 2px 0 0;
  font-size: 19px;
}

.ulke {
  color: #778197;
  font-size: 13px;
}

.genel-puan {
  display: grid;
  place-items: center;
  width: 58px;
  height: 58px;
  border-radius: 50%;
  background: linear-gradient(135deg, #e7effd, #f0e9fa);
  line-height: 1;
}

.genel-puan strong {
  color: #4c6089;
  font-size: 20px;
}

.genel-puan span {
  color: #8c89ab;
  font-size: 11px;
}

.rakamlar {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.rakamlar span {
  display: block;
  color: #778197;
  font-size: 12px;
}

.rakamlar strong {
  font-size: 15px;
  font-variant-numeric: tabular-nums;
}

.rakamlar .eksi {
  color: #b45f7b;
}

.grafik {
  display: flex;
  height: 12px;
  overflow: hidden;
  border-radius: 6px;
  background: #f1f4fb;
}

.grafik span + span {
  border-left: 2px solid white;
}

.dokum {
  display: grid;
  gap: 5px;
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 13px;
}

.dokum span {
  flex: 1;
  color: #778197;
}

.dokum strong {
  font-weight: 650;
  font-variant-numeric: tabular-nums;
}

.sec-buton {
  padding: 10px;
  background: #eee8fa;
  color: #6f5fa8;
}

.kart.secili .sec-buton {
  background: #a999d5;
  color: white;
}

.hepsi-buton {
  justify-self: center;
  padding: 9px 16px;
  border: 1px solid #e0deeb;
  background: white;
  color: #69728a;
}
</style>
