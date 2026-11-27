<script setup lang="ts">
// Ülke -> şehir seçimi. Seçenekler veritabanındaki şehirlerden gelir.
// v-model şehir adını taşır ('' = henüz karar verilmedi).
import { computed, onMounted, ref, watch } from 'vue'

interface Sehir {
  id: number
  name: string
  country: string
}

const model = defineModel<string>({ default: '' })
const props = defineProps<{ idOnEki?: string }>()

const sehirler = useState<Sehir[]>('secici-sehirler', () => [])
const hata = ref('')
const ulke = ref('')

const ulkeler = computed(() =>
  [...new Set(sehirler.value.map(s => s.country))].sort((a, b) => a.localeCompare(b, 'tr'))
)

const ulkedekiSehirler = computed(() =>
  sehirler.value
    .filter(s => s.country === ulke.value)
    .sort((a, b) => a.name.localeCompare(b.name, 'tr'))
)

// Dışarıdan gelen şehir adına göre ülkeyi ayarla (düzenleme, ön doldurma)
function ulkeyiEsle() {
  if (!model.value) return
  const bulunan = sehirler.value.find(
    s => s.name.toLocaleLowerCase('tr') === model.value.toLocaleLowerCase('tr')
  )
  if (bulunan) {
    ulke.value = bulunan.country
    model.value = bulunan.name
  }
}

function ulkeDegisti() {
  if (!ulkedekiSehirler.value.some(s => s.name === model.value)) {
    model.value = ''
  }
}

watch(model, ulkeyiEsle)

onMounted(async () => {
  if (!sehirler.value.length) {
    try {
      sehirler.value = await $fetch<Sehir[]>('/api/kesfet')
    } catch {
      hata.value = 'Şehir listesi yüklenemedi.'
    }
  }
  ulkeyiEsle()
})

const ulkeId = computed(() => `${props.idOnEki ?? 'sehir-secici'}-ulke`)
const sehirId = computed(() => `${props.idOnEki ?? 'sehir-secici'}-sehir`)
</script>

<template>
  <div class="secici">
    <div class="secici-alan">
      <label :for="ulkeId">Ülke</label>
      <select :id="ulkeId" v-model="ulke" @change="ulkeDegisti">
        <option value="">Henüz karar vermedim</option>
        <option v-for="u in ulkeler" :key="u" :value="u">{{ u }}</option>
      </select>
    </div>

    <div class="secici-alan">
      <label :for="sehirId">Şehir</label>
      <select :id="sehirId" v-model="model" :disabled="!ulke">
        <option value="">{{ ulke ? 'Şehir seç' : 'Önce ülke seç' }}</option>
        <option v-for="s in ulkedekiSehirler" :key="s.id" :value="s.name">{{ s.name }}</option>
      </select>
    </div>

    <p v-if="hata" class="secici-hata">{{ hata }}</p>
  </div>
</template>

<style scoped>
.secici {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  width: 100%;
}

.secici-alan {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.secici-alan label {
  color: #5b6478;
  font-size: 12px;
  font-weight: 800;
}

.secici-alan select {
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
  font-weight: 600;
}

.secici-alan select:disabled {
  background: #f6f4fb;
  color: var(--v-soft);
}

.secici-hata {
  grid-column: 1 / -1;
  margin: 0;
  color: var(--v-pink-deep);
  font-size: 13px;
}

@media (max-width: 560px) {
  .secici {
    grid-template-columns: 1fr;
  }
}
</style>
