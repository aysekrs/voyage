
<script setup lang="ts">
import { ref, watch, computed } from 'vue'

const props = defineProps<{ tripId: number }>()
const emit = defineEmits<{
  (e: 'kapat'): void
  (e: 'guncellendi'): void
}>()

const form = ref({
  title: '',
  destination: '',
  start_date: '',
  end_date: '',
  origin_city: '',
  origin_airport_code: '',
  budget_try: 0,
  people_count: 1,
  nature_weight: 25,
  food_weight: 25,
  history_weight: 25,
  nightlife_weight: 25
})

const yukleniyor = ref(false)
const kaydediliyor = ref(false)
const hata = ref('')
const basari = ref('')

const toplamAgirlik = computed(() =>
  form.value.nature_weight +
  form.value.food_weight +
  form.value.history_weight +
  form.value.nightlife_weight
)

async function seyahatiGetir() {
  yukleniyor.value = true
  hata.value = ''

  try {
    
const response = await fetch(`/api/trips/${props.tripId}`, {
  credentials: 'include'
})


    if (!response.ok) throw new Error('Seyahat bilgileri alınamadı.')

    const data = await response.json()

    form.value = {
      title: data.title ?? '',
      destination: data.destination ?? '',
      start_date: data.start_date?.slice(0, 10) ?? '',
      end_date: data.end_date?.slice(0, 10) ?? '',
      origin_city: data.origin_city ?? '',
      origin_airport_code: data.origin_airport_code ?? '',
      budget_try: Number(data.budget_try ?? 0),
      people_count: Number(data.people_count ?? 1),
      nature_weight: Number(data.nature_weight ?? 25),
      food_weight: Number(data.food_weight ?? 25),
      history_weight: Number(data.history_weight ?? 25),
      nightlife_weight: Number(data.nightlife_weight ?? 25)
    }
  } catch (error) {
    hata.value = error instanceof Error ? error.message : 'Hata oluştu.'
  } finally {
    yukleniyor.value = false
  }
}

async function kaydet() {
  hata.value = ''
  basari.value = ''

  if (toplamAgirlik.value !== 100) {
    hata.value = 'İlgi ağırlıklarının toplamı 100 olmalıdır.'
    return
  }

  kaydediliyor.value = true

  try {
    
const response = await fetch(`/api/trips/${props.tripId}`, {
  method: 'PUT',
  credentials: 'include',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(form.value)
})


    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(
        response.status === 401
          ? 'Oturum açmanız gerekiyor.'
          : error.message || error.statusMessage ||
            `Seyahat güncellenemedi (${response.status}).`
      )
    }

    basari.value = 'Seyahat başarıyla güncellendi.'
    emit('guncellendi')
  } catch (error) {
    hata.value = error instanceof Error ? error.message : 'Hata oluştu.'
  } finally {
    kaydediliyor.value = false
  }
}

function kalkisDegisti() {
  form.value.origin_airport_code = havalimanlari[form.value.origin_city] ?? form.value.origin_airport_code
}

const ILGI_ALANLARI = [
  { key: 'nature_weight', label: 'Doğa', ikon: '🌿' },
  { key: 'food_weight', label: 'Yeme & içme', ikon: '🍽️' },
  { key: 'history_weight', label: 'Kültür & tarih', ikon: '🏛️' },
  { key: 'nightlife_weight', label: 'Gece hayatı', ikon: '🌙' }
] as const

watch(() => props.tripId, seyahatiGetir, { immediate: true })
</script>

<template>
  <section class="duzenle">
    <div class="duzenle-ust">
      <div>
        <span class="v-ust-yazi">Seyahati düzenle</span>
        <h3>{{ form.title || 'Seyahat' }}</h3>
      </div>
      <button type="button" class="kapat" @click="emit('kapat')">× Kapat</button>
    </div>

    <p v-if="yukleniyor" class="durum">Bilgiler yükleniyor…</p>
    <p v-if="hata" class="durum hata">{{ hata }}</p>
    <p v-if="basari" class="durum basari">{{ basari }}</p>

    <form v-if="!yukleniyor" class="duzenle-form" @submit.prevent="kaydet">
      <div class="alan genis">
        <label for="duzenle-baslik">Seyahat adı</label>
        <input id="duzenle-baslik" v-model="form.title" required maxlength="150">
      </div>

      <div class="alan genis">
        <span class="etiket">Nereye?</span>
        <SehirSecici v-model="form.destination" :id-on-eki="`duzenle-${tripId}`" />
      </div>

      <div class="alan">
        <label for="duzenle-gidis">Gidiş</label>
        <input id="duzenle-gidis" v-model="form.start_date" type="date" required>
      </div>

      <div class="alan">
        <label for="duzenle-donus">Dönüş</label>
        <input id="duzenle-donus" v-model="form.end_date" type="date" :min="form.start_date" required>
      </div>

      <div class="alan">
        <label for="duzenle-kalkis">Kalkış şehri</label>
        <select id="duzenle-kalkis" v-model="form.origin_city" required @change="kalkisDegisti">
          <option v-if="form.origin_city && !(form.origin_city in havalimanlari)" :value="form.origin_city">
            {{ form.origin_city }}
          </option>
          <option v-for="(kod, sehir) in havalimanlari" :key="sehir" :value="sehir">
            {{ sehir }} ({{ kod }})
          </option>
        </select>
      </div>

      <div class="alan">
        <label for="duzenle-kod">Havalimanı kodu</label>
        <input id="duzenle-kod" v-model="form.origin_airport_code" required maxlength="10">
      </div>

      <div class="alan">
        <label for="duzenle-butce">Bütçe (TL)</label>
        <input id="duzenle-butce" v-model.number="form.budget_try" type="number" min="1" required>
      </div>

      <div class="alan">
        <label for="duzenle-kisi">Kişi sayısı</label>
        <input id="duzenle-kisi" v-model.number="form.people_count" type="number" min="1" required>
      </div>

      <div class="alan genis">
        <div class="agirlik-ust">
          <span class="etiket">İlgi alanların</span>
          <span class="toplam" :class="{ tamam: toplamAgirlik === 100 }">{{ toplamAgirlik }} / 100</span>
        </div>
        <div class="agirliklar">
          <label v-for="a in ILGI_ALANLARI" :key="a.key" class="agirlik">
            <span>{{ a.ikon }} {{ a.label }}</span>
            <input v-model.number="form[a.key]" type="range" min="0" max="100" step="5">
            <strong>{{ form[a.key] }}</strong>
          </label>
        </div>
      </div>

      <div class="butonlar genis">
        <button type="button" class="v-buton-ikincil" @click="emit('kapat')">İptal</button>
        <button type="submit" class="v-buton" :disabled="kaydediliyor || toplamAgirlik !== 100">
          {{ kaydediliyor ? 'Kaydediliyor…' : 'Değişiklikleri kaydet' }}
        </button>
      </div>
    </form>
  </section>
</template>

<style scoped>
.duzenle {
  padding: clamp(18px, 3vw, 28px);
  border: 1px solid #eeecf4;
  border-radius: 22px;
  background: white;
  color: var(--v-ink);
}

.duzenle-ust {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.duzenle-ust h3 {
  margin: 4px 0 0;
  font-size: 20px;
}

.kapat {
  padding: 8px 14px;
  border: 1px solid #e3e1ec;
  border-radius: 10px;
  background: white;
  color: var(--v-muted);
  font: inherit;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.durum {
  margin: 0 0 14px;
  padding: 10px 14px;
  border-radius: 12px;
  background: #f1f4fb;
  color: #687590;
  font-size: 14px;
}

.durum.hata {
  background: #fff1f4;
  color: var(--v-pink-deep);
}

.durum.basari {
  background: #eaf6f2;
  color: var(--v-mint);
}

.duzenle-form {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.genis {
  grid-column: 1 / -1;
}

.alan {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.alan label,
.etiket {
  color: #5b6478;
  font-size: 12px;
  font-weight: 800;
}

.alan input,
.alan select {
  width: 100%;
  min-width: 0;
  height: 48px;
  padding: 0 14px;
  border: 1px solid #dfdcea;
  border-radius: 13px;
  background: white;
  color: var(--v-ink);
  font: inherit;
  font-size: 15px;
}

.agirlik-ust {
  display: flex;
  justify-content: space-between;
}

.toplam {
  color: var(--v-pink-deep);
  font-size: 13px;
  font-weight: 800;
}

.toplam.tamam {
  color: var(--v-mint);
}

.agirliklar {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 20px;
  padding: 14px;
  border-radius: 16px;
  background: var(--v-surface-soft);
}

.agirlik {
  display: grid;
  grid-template-columns: 1fr 40px;
  align-items: center;
  gap: 4px 10px;
  font-size: 14px;
}

.agirlik span {
  grid-column: 1 / -1;
  color: #4c566b;
  font-weight: 700;
}

.agirlik input {
  height: auto;
  padding: 0;
  border: 0;
  accent-color: var(--v-lilac-deep);
}

.agirlik strong {
  color: var(--v-lilac-deep);
  text-align: right;
}

.butonlar {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

@media (max-width: 640px) {
  .duzenle-form,
  .agirliklar {
    grid-template-columns: 1fr;
  }
}
</style>
