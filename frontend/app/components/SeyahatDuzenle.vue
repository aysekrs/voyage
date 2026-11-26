
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
      throw new Error(
        response.status === 401
          ? 'Oturum açmanız gerekiyor.'
          : `Seyahat güncellenemedi (${response.status}).`
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

watch(() => props.tripId, seyahatiGetir, { immediate: true })
</script>

<template>
  <section>
    <h2>✏️ Seyahat Düzenle</h2>

    <p v-if="yukleniyor">Bilgiler yükleniyor...</p>
    <p v-if="hata" style="color: red">{{ hata }}</p>
    <p v-if="basari" style="color: green">{{ basari }}</p>

    <form v-if="!yukleniyor" @submit.prevent="kaydet">
      <label>Seyahat Adı</label>
      <input v-model="form.title" required maxlength="150" />

      <label>Gidilecek Yer</label>
      <input v-model="form.destination" required maxlength="150" />

      <label>Başlangıç Tarihi</label>
      <input v-model="form.start_date" type="date" required />

      <label>Bitiş Tarihi</label>
      <input v-model="form.end_date" type="date" required />

      <label>Kalkış Şehri</label>
      <input v-model="form.origin_city" required />

      <label>Havalimanı Kodu</label>
      <input v-model="form.origin_airport_code" required maxlength="10" />

      <label>Bütçe (TL)</label>
      <input v-model.number="form.budget_try" type="number" min="1" required />

      <label>Kişi Sayısı</label>
      <input v-model.number="form.people_count" type="number" min="1" required />

      <label>Doğa (%)</label>
      <input v-model.number="form.nature_weight" type="number" min="0" max="100" />

      <label>Yemek (%)</label>
      <input v-model.number="form.food_weight" type="number" min="0" max="100" />

      <label>Tarih (%)</label>
      <input v-model.number="form.history_weight" type="number" min="0" max="100" />

      <label>Gece Hayatı (%)</label>
      <input v-model.number="form.nightlife_weight" type="number" min="0" max="100" />

      <p>Toplam: {{ toplamAgirlik }} / 100</p>

      <button type="submit" :disabled="kaydediliyor || toplamAgirlik !== 100">
        {{ kaydediliyor ? 'Kaydediliyor...' : 'Değişiklikleri Kaydet' }}
      </button>

      <button type="button" @click="emit('kapat')">
        İptal
      </button>
    </form>
  </section>
</template>
