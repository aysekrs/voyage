<script setup lang="ts">
// Kalkış havalimanı arama kutusu: yazdıkça dünyadaki tarifeli havalimanlarını önerir.
// Sadece listeden seçim kabul edilir; serbest yazılan metin formu geçersiz yapar.
//
// Kullanım:
//   <HavalimaniSecici v-model="form.origin_airport_code" v-model:sehir="form.origin_city" required />
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'

interface Havalimani {
  iata: string
  name: string
  label: string
  city_display: string
  country_display: string
  type: string
}

const props = withDefaults(defineProps<{
  modelValue?: string | null
  sehir?: string | null
  id?: string
  placeholder?: string
  required?: boolean
  // sade: ana sayfa arama çubuğu gibi kenarlıksız alanlar için
  sade?: boolean
}>(), {
  modelValue: '',
  sehir: '',
  id: undefined,
  placeholder: 'Şehir, havalimanı ya da kod yaz (örn. Münih, IST)',
  required: false,
  sade: false
})

const emit = defineEmits<{
  'update:modelValue': [kod: string]
  'update:sehir': [sehir: string]
  secildi: [havalimani: Havalimani | null]
}>()

const girdi = ref<HTMLInputElement | null>(null)
const metin = ref('')
const sonuclar = ref<Havalimani[]>([])
const acik = ref(false)
const aktif = ref(-1)
const yukleniyor = ref(false)
const listeId = `hs-liste-${Math.random().toString(36).slice(2, 8)}`
let zamanlayici: ReturnType<typeof setTimeout> | null = null
let istekNo = 0

function kisaAd(h: { city_display: string; iata: string }) {
  return `${h.city_display} (${h.iata})`
}

function gecerlilikAyarla() {
  if (!girdi.value) return
  const bos = !props.modelValue
  if (bos && metin.value.trim()) {
    girdi.value.setCustomValidity('Listeden bir havalimanı seç.')
  } else if (bos && props.required) {
    girdi.value.setCustomValidity('Kalkış havalimanını seç.')
  } else {
    girdi.value.setCustomValidity('')
  }
}

// Dışarıdan gelen kod (düzenleme formu, asistan kartı) varsa kutuyu doldur
async function kodaGoreDoldur(kod: string | null | undefined) {
  if (!kod) {
    gecerlilikAyarla()
    return
  }
  if (metin.value.includes(`(${kod})`)) return
  metin.value = props.sehir ? `${props.sehir} (${kod})` : kod
  try {
    const h = await $fetch<Havalimani>(`/api/havalimanlari/${encodeURIComponent(kod)}`)
    if (props.modelValue === kod) metin.value = kisaAd(h)
  } catch {
    // Kod tabloda yoksa metin olduğu gibi kalır; backend kaydı reddeder.
  }
  gecerlilikAyarla()
}

watch(() => props.modelValue, kod => kodaGoreDoldur(kod))
onMounted(() => kodaGoreDoldur(props.modelValue))

async function ara(q: string) {
  const buIstek = ++istekNo
  yukleniyor.value = true
  try {
    const liste = await $fetch<Havalimani[]>('/api/havalimanlari', { query: { q } })
    if (buIstek !== istekNo) return
    sonuclar.value = liste
    aktif.value = liste.length ? 0 : -1
  } catch {
    if (buIstek === istekNo) sonuclar.value = []
  } finally {
    if (buIstek === istekNo) yukleniyor.value = false
  }
}

function yazildi() {
  // Kullanıcı yazmaya başlayınca önceki seçim geçersiz olur
  if (props.modelValue) {
    emit('update:modelValue', '')
    emit('update:sehir', '')
    emit('secildi', null)
  }
  acik.value = true
  if (zamanlayici) clearTimeout(zamanlayici)
  zamanlayici = setTimeout(() => ara(metin.value), 200)
  gecerlilikAyarla()
}

function odaklandi() {
  acik.value = true
  ara(props.modelValue ? '' : metin.value)
}

function sec(h: Havalimani) {
  metin.value = kisaAd(h)
  emit('update:modelValue', h.iata)
  emit('update:sehir', h.city_display)
  emit('secildi', h)
  acik.value = false
  girdi.value?.setCustomValidity('')
}

function tus(e: KeyboardEvent) {
  if (!acik.value && (e.key === 'ArrowDown' || e.key === 'ArrowUp')) {
    odaklandi()
    return
  }
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    aktif.value = Math.min(aktif.value + 1, sonuclar.value.length - 1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    aktif.value = Math.max(aktif.value - 1, 0)
  } else if (e.key === 'Enter' && acik.value && sonuclar.value[aktif.value]) {
    e.preventDefault()
    sec(sonuclar.value[aktif.value]!)
  } else if (e.key === 'Escape') {
    acik.value = false
  }
}

function ayrildi() {
  // Tıklama ile seçime izin vermek için kısa gecikme
  setTimeout(() => {
    acik.value = false
    gecerlilikAyarla()
  }, 150)
}

onBeforeUnmount(() => {
  if (zamanlayici) clearTimeout(zamanlayici)
})
</script>

<template>
  <div :class="['hs', { sade }]">
    <input
      :id="id"
      ref="girdi"
      v-model="metin"
      type="text"
      role="combobox"
      autocomplete="off"
      :aria-expanded="acik"
      :aria-controls="listeId"
      :aria-activedescendant="aktif >= 0 ? `${listeId}-${aktif}` : undefined"
      :placeholder="placeholder"
      :required="required"
      @input="yazildi"
      @focus="odaklandi"
      @blur="ayrildi"
      @keydown="tus"
    >
    <ul v-show="acik && (sonuclar.length || yukleniyor || metin.trim().length >= 2)" :id="listeId" class="hs-liste" role="listbox">
      <li v-if="yukleniyor && !sonuclar.length" class="hs-bilgi">Aranıyor...</li>
      <li v-else-if="!sonuclar.length" class="hs-bilgi">Bu adla havalimanı bulunamadı.</li>
      <li
        v-for="(h, i) in sonuclar"
        :id="`${listeId}-${i}`"
        :key="h.iata"
        role="option"
        :aria-selected="i === aktif"
        :class="['hs-oge', { aktif: i === aktif }]"
        @mousedown.prevent="sec(h)"
        @mouseenter="aktif = i"
      >
        <span class="hs-kod">{{ h.iata }}</span>
        <span class="hs-yazi">
          <strong>{{ h.city_display }}</strong>
          <small>{{ h.name }} · {{ h.country_display }}</small>
        </span>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.hs {
  position: relative;
  width: 100%;
}

.hs input {
  width: 100%;
  box-sizing: border-box;
  padding: 12px 14px;
  border: 1px solid #e3e1ec;
  border-radius: 14px;
  background: white;
  color: var(--v-ink);
  font: inherit;
}

.hs.sade input {
  padding: 2px 0 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  color: var(--v-muted);
  font-size: 14px;
}

.hs.sade input:focus {
  border: 0;
  box-shadow: none;
}

.hs-liste {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  z-index: 70;
  width: max(100%, 320px);
  max-height: 320px;
  margin: 0;
  padding: 6px;
  overflow-y: auto;
  list-style: none;
  border: 1px solid #eeecf4;
  border-radius: 16px;
  background: white;
  box-shadow: var(--v-shadow);
}

.hs-oge {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 9px 10px;
  border-radius: 12px;
  cursor: pointer;
}

.hs-oge.aktif {
  background: var(--v-surface-soft);
}

.hs-kod {
  flex: none;
  width: 44px;
  padding: 4px 0;
  border-radius: 8px;
  background: var(--v-gradient-soft);
  color: var(--v-lilac-deep);
  font-size: 13px;
  font-weight: 800;
  text-align: center;
}

.hs-yazi {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.hs-yazi strong {
  color: var(--v-ink);
  font-size: 14px;
}

.hs-yazi small {
  overflow: hidden;
  color: var(--v-muted);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hs-bilgi {
  padding: 10px;
  color: var(--v-muted);
  font-size: 13px;
}
</style>
