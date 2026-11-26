<script setup lang="ts">
// 5. hafta (Kişi B): AI asistan sohbeti + "anladığım bilgiler" onay kartı
import { ref, computed, nextTick, onMounted } from 'vue'

interface Mesaj {
  id: number | string
  role: 'user' | 'assistant'
  content: string
  trip_id?: number | null
}

interface Bilgi {
  origin_city: string | null
  destination: string | null
  origin_airport_code: string | null
  budget_try: number | null
  people_count: number | null
  start_date: string | null
  end_date: string | null
  nature_weight: number | null
  food_weight: number | null
  history_weight: number | null
  nightlife_weight: number | null
}

interface Durum {
  bilgi: Partial<Bilgi>
  eksik: string[]
  hatalar: string[]
  hazir: boolean
  kaynak: 'llm' | 'kural' | null
}

// kompakt: sağ alttaki asistan balonunun dar paneli için (sekmeli görünüm)
const props = withDefaults(defineProps<{ kompakt?: boolean }>(), { kompakt: false })
const emit = defineEmits<{ olusturuldu: [id: number] }>()
const sekme = ref<'sohbet' | 'kart'>('sohbet')

const ORNEKLER = [
  "İzmir'den 2 kişi 15-20 Temmuz arası 40 bin TL bütçeyle, tarih ve yemek ağırlıklı bir tatil",
  "Eşimle Ankara çıkışlı 10 Mayıs'ta 4 gece, doğa ve deniz olsun, gece hayatı istemiyorum",
  "İstanbul'dan 3 kişi, bütçemiz 90 bin TL, müzeleri ve gece hayatını seviyoruz"
]

const AGIRLIK_ALANLARI = [
  { anahtar: 'nature_weight', ad: '🌿 Doğa' },
  { anahtar: 'food_weight', ad: '🍽️ Yemek' },
  { anahtar: 'history_weight', ad: '🏛️ Tarih' },
  { anahtar: 'nightlife_weight', ad: '🌙 Gece hayatı' }
] as const

const HOSGELDIN: Mesaj = {
  id: 'hosgeldin',
  role: 'assistant',
  content: 'Merhaba! Nasıl bir seyahat düşündüğünü bir cümleyle anlat: nereden yola çıkacaksın, ne zaman, kaç kişi, bütçen ve neleri seversin. Eksik kalanı ben sorarım.'
}

const mesajlar = ref<Mesaj[]>([])
const durum = ref<Durum | null>(null)
const kart = ref<Bilgi>(bosBilgi())
const girdi = ref('')
const gonderiliyor = ref(false)
const onaylaniyor = ref(false)
const yukleniyor = ref(true)
const hata = ref('')
const liste = ref<HTMLElement | null>(null)
const sehirAdlari = ref<string[]>([])

// Seyahat oluşturulan sohbetin son mesajı: altına seyahat bağlantısı ve ayraç gelir
function seyahatMesajiMi(m: Mesaj) {
  return m.role === 'assistant' && !!m.trip_id && m.content.startsWith('Seyahatin oluşturuldu')
}

function bosBilgi(): Bilgi {
  return {
    origin_city: null, destination: null, origin_airport_code: null, budget_try: null, people_count: null,
    start_date: null, end_date: null,
    nature_weight: null, food_weight: null, history_weight: null, nightlife_weight: null
  }
}

// Önce seyahate dönüşmüş eski sohbetler, sonra karşılama, sonra açık sohbet
const gorunenMesajlar = computed(() => [
  ...mesajlar.value.filter(m => m.trip_id),
  HOSGELDIN,
  ...mesajlar.value.filter(m => !m.trip_id)
])
const kartVar = computed(() => Object.values(durum.value?.bilgi ?? {}).some(v => v !== null && v !== undefined))
const agirlikToplami = computed(() =>
  AGIRLIK_ALANLARI.reduce((t, a) => t + (Number(kart.value[a.anahtar]) || 0), 0)
)
const kartTamam = computed(() => {
  const k = kart.value
  return Boolean(
    k.origin_city && k.origin_airport_code && Number(k.budget_try) > 0 && Number(k.people_count) > 0 &&
    k.start_date && k.end_date && k.end_date > k.start_date && agirlikToplami.value === 100
  )
})

function eksikMi(alan: string) {
  if (alan.endsWith('_weight')) return durum.value?.eksik.includes('interests')
  return durum.value?.eksik.includes(alan)
}

function durumuUygula(yeni: Durum) {
  durum.value = yeni
  kart.value = { ...bosBilgi(), ...yeni.bilgi }
}

async function asagiKaydir() {
  await nextTick()
  liste.value?.scrollTo({ top: liste.value.scrollHeight, behavior: 'smooth' })
}

onMounted(async () => {
  // Gidilecek şehir kutusu için öneri listesi (hata olursa kutu yine elle yazılabilir)
  $fetch<{ name: string }[]>('/api/kesfet')
    .then(liste => { sehirAdlari.value = liste.map(s => s.name).sort((a, b) => a.localeCompare(b, 'tr')) })
    .catch(() => {})
  await yukle()
})

// Sohbeti sunucudan yeniden al (asistan paneli her açıldığında çağrılır;
// böylece başka sayfada silinen seyahatlerin mesajları ekranda kalmaz)
async function yukle() {
  if (gonderiliyor.value || onaylaniyor.value) return
  try {
    const veri = await $fetch<{ messages: Mesaj[]; durum: Durum }>('/api/ai/chat')
    mesajlar.value = veri.messages
    durumuUygula(veri.durum)
    hata.value = ''
  } catch (err: any) {
    hata.value = err?.data?.message || 'Sohbet yüklenemedi.'
  } finally {
    yukleniyor.value = false
    asagiKaydir()
  }
}

defineExpose({ yukle })

async function gonder(metin?: string) {
  const mesaj = (metin ?? girdi.value).trim()
  if (!mesaj || gonderiliyor.value) return
  hata.value = ''
  gonderiliyor.value = true
  // Kullanıcının mesajını hemen göster
  const gecici: Mesaj = { id: `gecici-${Date.now()}`, role: 'user', content: mesaj }
  mesajlar.value.push(gecici)
  girdi.value = ''
  asagiKaydir()
  try {
    const veri = await $fetch<{ messages: Mesaj[]; durum: Durum }>('/api/ai/chat', {
      method: 'POST',
      body: { message: mesaj }
    })
    mesajlar.value = [...mesajlar.value.filter(m => m.id !== gecici.id), ...veri.messages]
    durumuUygula(veri.durum)
  } catch (err: any) {
    mesajlar.value = mesajlar.value.filter(m => m.id !== gecici.id)
    girdi.value = mesaj
    hata.value = err?.data?.message || 'Asistan şu an cevap veremiyor.'
  } finally {
    gonderiliyor.value = false
    asagiKaydir()
  }
}

async function yeniSohbet() {
  hata.value = ''
  try {
    await $fetch('/api/ai/chat', { method: 'DELETE' })
    // Seyahate dönüşmüş eski sohbetler kalır, yarım kalan sohbet silinir
    mesajlar.value = mesajlar.value.filter(m => m.trip_id)
    durum.value = null
    kart.value = bosBilgi()
  } catch (err: any) {
    hata.value = err?.data?.message || 'Sohbet silinemedi.'
  }
}

async function onayla() {
  if (!kartTamam.value || onaylaniyor.value) return
  hata.value = ''
  onaylaniyor.value = true
  try {
    const veri = await $fetch<{ trip: { id: number } }>('/api/ai/onayla', {
      method: 'POST',
      body: {
        ...kart.value,
        destination: kart.value.destination?.trim() || null,
        origin_airport_code: kart.value.origin_airport_code?.toUpperCase() ?? null,
        budget_try: Number(kart.value.budget_try),
        people_count: Number(kart.value.people_count),
        ...Object.fromEntries(AGIRLIK_ALANLARI.map(a => [a.anahtar, Number(kart.value[a.anahtar]) || 0]))
      }
    })
    emit('olusturuldu', veri.trip.id)
  } catch (err: any) {
    hata.value = err?.data?.message || 'Seyahat oluşturulamadı.'
  } finally {
    onaylaniyor.value = false
  }
}
</script>

<template>
  <div :class="['ai-izgara', { kompakt: props.kompakt }]">
    <div v-if="props.kompakt" class="sekmeler" role="tablist">
      <button type="button" role="tab" :aria-selected="sekme === 'sohbet'"
        :class="['v-cip', { aktif: sekme === 'sohbet' }]" @click="sekme = 'sohbet'">💬 Sohbet</button>
      <button type="button" role="tab" :aria-selected="sekme === 'kart'"
        :class="['v-cip', { aktif: sekme === 'kart' }]" @click="sekme = 'kart'">
        📝 Bilgiler <span v-if="durum?.hazir" class="hazir-nokta" aria-label="hazır" />
      </button>
    </div>

    <!-- Sohbet -->
    <section v-show="!props.kompakt || sekme === 'sohbet'" class="sohbet v-kart">
      <div class="sohbet-ust">
        <div>
          <p class="v-ust-yazi">AI asistan</p>
          <h2 class="v-baslik">Seyahatini anlat</h2>
        </div>
        <button v-if="mesajlar.some(m => !m.trip_id)" type="button" class="v-buton-ikincil" @click="yeniSohbet">Yeni sohbet</button>
      </div>

      <div ref="liste" class="mesajlar" aria-live="polite">
        <p v-if="yukleniyor" class="b-not">Yükleniyor...</p>
        <template v-for="m in gorunenMesajlar" :key="m.id">
          <div :class="['balon', m.role === 'user' ? 'kullanici' : 'asistan', { eski: m.trip_id }]">
            {{ m.content }}
            <NuxtLink v-if="seyahatMesajiMi(m)" :to="`/seyahatler/${m.trip_id}`" class="seyahat-link">
              Seyahati aç →
            </NuxtLink>
          </div>
          <div v-if="seyahatMesajiMi(m)" class="ayrac"><span>Yeni sohbet</span></div>
        </template>
        <div v-if="gonderiliyor" class="balon asistan yaziyor">Düşünüyorum…</div>
        <button v-if="props.kompakt && durum?.hazir && mesajlar.some(m => !m.trip_id)" type="button"
          class="v-buton kart-gecis" @click="sekme = 'kart'">
          Bilgiler hazır, kontrol et ve onayla →
        </button>
      </div>

      <div v-if="!mesajlar.some(m => !m.trip_id) && !yukleniyor" class="ornekler">
        <p class="b-durak-alt">Örnek cümleler:</p>
        <button v-for="o in ORNEKLER" :key="o" type="button" class="v-cip ornek" @click="gonder(o)">{{ o }}</button>
      </div>

      <form class="yazma" @submit.prevent="gonder()">
        <textarea
          v-model="girdi"
          rows="2"
          maxlength="1000"
          placeholder="Örn. İzmir'den 2 kişi 15-20 Temmuz, 40 bin TL, tarih ve yemek"
          :disabled="gonderiliyor"
          @keydown.enter.exact.prevent="gonder()"
        />
        <button type="submit" class="v-buton" :disabled="gonderiliyor || !girdi.trim()">Gönder</button>
      </form>
      <p v-if="hata" class="b-hata" role="alert">{{ hata }}</p>
    </section>

    <!-- Onay kartı -->
    <aside v-show="!props.kompakt || sekme === 'kart'" class="kart v-kart">
      <p class="v-ust-yazi">Anladığım bilgiler</p>
      <h2 class="v-baslik kart-baslik">Kontrol et ve onayla</h2>
      <p v-if="!kartVar" class="b-aciklama">Sen yazdıkça anladığım bilgiler burada görünecek. Yanlış olanı buradan düzeltebilirsin.</p>

      <form v-else class="alanlar" @submit.prevent="onayla">
        <label :class="{ eksik: eksikMi('origin_city') }">Kalkış şehri
          <input v-model="kart.origin_city" type="text" maxlength="150" />
        </label>
        <label class="genis">Gidilecek şehir (isteğe bağlı)
          <input v-model="kart.destination" type="text" list="ai-sehirler" maxlength="150"
            placeholder="Boş bırakırsan sonra önerilerden seçersin" />
          <datalist id="ai-sehirler">
            <option v-for="ad in sehirAdlari" :key="ad" :value="ad" />
          </datalist>
        </label>
        <label :class="{ eksik: eksikMi('origin_airport_code') }">Havalimanı kodu
          <input v-model="kart.origin_airport_code" type="text" maxlength="3" style="text-transform: uppercase" />
        </label>
        <label :class="{ eksik: eksikMi('start_date') }">Gidiş
          <input v-model="kart.start_date" type="date" />
        </label>
        <label :class="{ eksik: eksikMi('end_date') }">Dönüş
          <input v-model="kart.end_date" type="date" />
        </label>
        <label :class="{ eksik: eksikMi('budget_try') }">Bütçe (TL)
          <input v-model.number="kart.budget_try" type="number" min="1" step="any" inputmode="decimal" />
        </label>
        <label :class="{ eksik: eksikMi('people_count') }">Kişi sayısı
          <input v-model.number="kart.people_count" type="number" min="1" max="20" />
        </label>

        <fieldset :class="['agirliklar', { eksik: eksikMi('nature_weight') }]">
          <legend>İlgi alanları <span :class="{ uyari: agirlikToplami !== 100 }">(toplam {{ agirlikToplami }}/100)</span></legend>
          <label v-for="a in AGIRLIK_ALANLARI" :key="a.anahtar">{{ a.ad }}
            <input v-model.number="kart[a.anahtar]" type="number" min="0" max="100" step="1" />
          </label>
        </fieldset>

        <ul v-if="durum?.hatalar.length" class="b-uyari hata-listesi">
          <li v-for="h in durum.hatalar" :key="h">{{ h }}</li>
        </ul>

        <button type="submit" class="v-buton onay" :disabled="!kartTamam || onaylaniyor">
          {{ onaylaniyor ? 'Seyahat oluşturuluyor...' : 'Onayla ve seyahati oluştur' }}
        </button>
        <p class="b-not">
          <template v-if="!kart.destination">Gidilecek şehri bir sonraki adımda, bütçene ve ilgi alanlarına göre önerilen şehirlerden seçeceksin.</template>
          <span v-if="durum?.kaynak === 'kural'"> (Yapay zekâ anahtarı tanımlı değil; bilgiler kurallarla çıkarıldı.)</span>
        </p>
      </form>
    </aside>
  </div>
</template>

<style scoped>
.ai-izgara {
  display: grid;
  gap: 20px;
  margin-top: 24px;
}

@media (min-width: 1024px) {
  .ai-izgara {
    grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
    align-items: start;
  }
}

.sohbet,
.kart {
  padding: clamp(18px, 3vw, 28px);
}

/* ---------- Kompakt (asistan balonu paneli) ---------- */
.kompakt {
  display: block;
  margin-top: 0;
}

.kompakt .sekmeler {
  display: flex;
  gap: 8px;
  padding: 12px 16px 0;
}

.kompakt .sekmeler .v-cip {
  padding: 8px 14px;
  font-size: 13px;
}

.hazir-nokta {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--v-mint);
}

.kompakt .sohbet,
.kompakt .kart {
  padding: 12px 16px 16px;
  border: 0;
  border-radius: 0;
  box-shadow: none;
}

.kompakt .sohbet-ust > div,
.kompakt .kart > .v-ust-yazi {
  display: none;
}

.kompakt .sohbet-ust {
  justify-content: flex-end;
}

.kompakt .mesajlar {
  height: min(360px, calc(100dvh - 330px));
  margin-top: 8px;
}

.kompakt .kart-baslik {
  font-size: 18px;
}

.kompakt .alanlar {
  margin-top: 12px;
}

.kart-gecis {
  align-self: center;
  margin-top: 4px;
  padding: 10px 16px;
  font-size: 14px;
}

.sohbet-ust {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.mesajlar {
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 420px;
  margin-top: 18px;
  padding: 16px;
  overflow-y: auto;
  border-radius: 20px;
  background: var(--v-surface-soft);
}

.balon {
  max-width: 85%;
  padding: 12px 16px;
  border-radius: 18px;
  line-height: 1.5;
  white-space: pre-wrap;
}

.balon.asistan {
  align-self: flex-start;
  border: 1px solid #eeecf4;
  border-bottom-left-radius: 6px;
  background: white;
  color: var(--v-ink);
}

.balon.kullanici {
  align-self: flex-end;
  border-bottom-right-radius: 6px;
  background: var(--v-gradient-button);
  color: white;
  font-weight: 600;
}

.balon.eski {
  opacity: 0.75;
}

.seyahat-link {
  display: inline-block;
  margin-top: 8px;
  color: var(--v-lilac-deep);
  font-weight: 800;
  text-decoration: none;
}

.ayrac {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 6px 0;
  color: var(--v-soft);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 1.2px;
  text-transform: uppercase;
}

.ayrac::before,
.ayrac::after {
  content: "";
  flex: 1;
  height: 1px;
  background: var(--v-line);
}

.alanlar .genis {
  grid-column: 1 / -1;
}

.yaziyor {
  color: var(--v-muted) !important;
  font-style: italic;
}

.ornekler {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  margin-top: 14px;
}

.ornek {
  white-space: normal;
  text-align: left;
}

.yazma {
  display: flex;
  gap: 10px;
  margin-top: 14px;
}

.yazma textarea {
  flex: 1;
  padding: 12px 14px;
  border: 1px solid #e3e1ec;
  border-radius: 14px;
  color: var(--v-ink);
  font: inherit;
  resize: none;
}

.kart-baslik {
  font-size: 22px;
}

.alanlar {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 18px;
}

.alanlar label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: var(--v-muted);
  font-size: 13px;
  font-weight: 700;
}

.alanlar input {
  padding: 10px 12px;
  border: 1px solid #e3e1ec;
  border-radius: 12px;
  color: var(--v-ink);
  font: inherit;
  font-weight: 600;
}

.alanlar .eksik input,
.agirliklar.eksik {
  border-color: var(--v-pink);
  background: #fff7fa;
}

.agirliklar {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-column: 1 / -1;
  gap: 10px;
  margin: 0;
  padding: 14px;
  border: 1px solid #eeecf4;
  border-radius: 16px;
}

.agirliklar legend {
  padding: 0 6px;
  color: var(--v-ink);
  font-weight: 800;
}

.agirliklar .uyari {
  color: var(--v-pink-deep);
}

.hata-listesi {
  grid-column: 1 / -1;
  margin: 0;
  padding-left: 30px;
}

.onay {
  grid-column: 1 / -1;
}

.alanlar .b-not {
  grid-column: 1 / -1;
  margin: 0;
}
</style>
