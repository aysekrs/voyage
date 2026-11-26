
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import UcusSonuclari from './UcusSonuclari.vue'
import OtelSonuclari from './OtelSonuclari.vue'
import SehirOnerileri from './SehirOnerileri.vue'

interface SeyahatDetay {
  id: number
  title: string
  destination: string | null
  selected_destination_id: number | null
  start_date: string
  end_date: string
  origin_city: string | null
  origin_airport_code: string | null
  budget_try: number | string | null
  people_count: number | null
  status: string
  role: string
  created_at: string
}

const props = defineProps<{ tripId: number }>()
const emit = defineEmits<{ (e: 'kapat'): void }>()

const seyahat = ref<SeyahatDetay | null>(null)
const yukleniyor = ref(false)
const hata = ref('')

async function detayGetir(id: number) {
  yukleniyor.value = true
  hata.value = ''
  seyahat.value = null

  try {
    const response = await fetch(`/api/trips/${id}`, {
      credentials: 'include'
    })

    if (!response.ok) {
      throw new Error(
        response.status === 401
          ? 'Seyahat detaylarını görmek için giriş yapmalısınız.'
          : `Seyahat detayları alınamadı (${response.status}).`
      )
    }

    seyahat.value = await response.json()
  } catch (error) {
    hata.value = error instanceof Error
      ? error.message
      : 'Bir hata oluştu.'
  } finally {
    yukleniyor.value = false
  }
}

function tarihFormatla(tarih: string | null | undefined) {
  if (!tarih) return '-'

  const [yil, ay, gun] = tarih.slice(0, 10).split('-')
  return `${gun}.${ay}.${yil}`
}

function butceFormatla(butce: number | string | null) {
  if (butce === null || butce === undefined || butce === '') {
    return 'Belirtilmedi'
  }

  const sayi = Number(butce)

  if (!Number.isFinite(sayi)) {
    return 'Belirtilmedi'
  }

  return new Intl.NumberFormat('tr-TR', {
    style: 'currency',
    currency: 'TRY',
    maximumFractionDigits: 2
  }).format(sayi)
}

const geceSayisi = computed(() => {
  if (!seyahat.value) return null

  const baslangic = Date.parse(
    `${seyahat.value.start_date.slice(0, 10)}T00:00:00Z`
  )

  const bitis = Date.parse(
    `${seyahat.value.end_date.slice(0, 10)}T00:00:00Z`
  )

  if (!Number.isFinite(baslangic) || !Number.isFinite(bitis)) {
    return null
  }

  const fark = Math.round(
    (bitis - baslangic) / (1000 * 60 * 60 * 24)
  )

  return fark >= 0 ? fark : null
})

// Sekmeler: şehir seçilmemişse "Şehir seç", seçilmişse "Uçuşlar" ile açılır
type Sekme = 'sehir' | 'ucus' | 'otel'
const sekme = ref<Sekme | null>(null)

watch(seyahat, yeni => {
  if (yeni && sekme.value === null) {
    sekme.value = yeni.selected_destination_id ? 'ucus' : 'sehir'
  }
})

// Şehir önerilerinden biri seçilince detayı tazele ve uçuşlara geç
async function secimSonrasiYenile() {
  sekme.value = 'ucus'
  try {
    const response = await fetch(`/api/trips/${props.tripId}`, {
      credentials: 'include'
    })
    if (response.ok) seyahat.value = await response.json()
  } catch {
    // sessizce geç; seçim zaten kaydedildi
  }
}

watch(
  () => props.tripId,
  id => detayGetir(id),
  { immediate: true }
)
</script>

<template>
  <section class="trip-detail">

    <div v-if="yukleniyor" class="detail-state">
      Seyahat bilgileri yükleniyor...
    </div>

    <div v-else-if="hata" class="detail-state error-state">
      {{ hata }}
    </div>

    <template v-else-if="seyahat">
      <!-- Seyahat özeti -->
      <div class="detail-overview">
        <div class="overview-main">
          <span class="overview-eyebrow">
            SEYAHAT PLANIN
          </span>

          <h2>{{ seyahat.title }}</h2>

          <div class="overview-route">
            <div class="route-place">
              <span class="route-caption">NEREDEN</span>
              <strong>
                {{ seyahat.origin_city || 'Belirtilmedi' }}
              </strong>
              <span>{{ seyahat.origin_airport_code || '—' }}</span>
            </div>

            <div class="route-line" aria-hidden="true">
              <span class="route-circle"></span>
              <span class="route-dashes"></span>
              <span class="route-plane">✈</span>
              <span class="route-dashes"></span>
              <span class="route-circle"></span>
            </div>

            <div class="route-place">
              <span class="route-caption">NEREYE</span>
              <strong>{{ seyahat.destination || 'Henüz seçilmedi' }}</strong>
              <span>Varış noktası</span>
            </div>
          </div>

          <div class="overview-dates">
            <span>
              {{ tarihFormatla(seyahat.start_date) }}
              —
              {{ tarihFormatla(seyahat.end_date) }}
            </span>

            <span v-if="geceSayisi !== null" class="night-badge">
              {{ geceSayisi }} gece
            </span>
          </div>
        </div>

        <div class="overview-decoration" aria-hidden="true">
          <div class="decoration-sun"></div>
          <div class="decoration-hill hill-back"></div>
          <div class="decoration-hill hill-front"></div>
        </div>
      </div>

      <!-- Bilgi alanı -->
      <div class="detail-facts">
        <div class="fact">
          <span class="fact-icon fact-blue">₺</span>
          <div>
            <span class="fact-label">Toplam bütçe</span>
            <strong>{{ butceFormatla(seyahat.budget_try) }}</strong>
          </div>
        </div>

        <div class="fact">
          <span class="fact-icon fact-lilac">♙</span>
          <div>
            <span class="fact-label">Yolcu sayısı</span>
            <strong>
              {{ seyahat.people_count ?? 'Belirtilmedi' }}
            </strong>
          </div>
        </div>

        <div class="fact">
          <span class="fact-icon fact-pink">✓</span>
          <div>
            <span class="fact-label">Seyahat durumu</span>
            <strong>{{ seyahat.status }}</strong>
          </div>
        </div>

        <div class="fact">
          <span class="fact-icon fact-blue">◷</span>
          <div>
            <span class="fact-label">Oluşturulma tarihi</span>
            <strong>
              {{ tarihFormatla(seyahat.created_at) }}
            </strong>
          </div>
        </div>
      </div>

      <div class="detail-role">
        <span>
          Seyahatteki rolün:
          <strong>
            {{ seyahat.role === 'owner' ? 'Sahip' : seyahat.role }}
          </strong>
        </span>
      </div>

      <!-- Sekmeler -->
      <nav class="sekmeler" aria-label="Seyahat adımları">
        <button
          type="button"
          class="sekme"
          :class="{ aktif: sekme === 'sehir' }"
          @click="sekme = 'sehir'"
        >
          <span class="sekme-no">1</span>
          {{ seyahat.selected_destination_id ? 'Şehri değiştir' : 'Şehir seç' }}
        </button>
        <button
          type="button"
          class="sekme"
          :class="{ aktif: sekme === 'ucus' }"
          @click="sekme = 'ucus'"
        >
          <span class="sekme-no">2</span>
          Uçuşlar
        </button>
        <button
          type="button"
          class="sekme"
          :class="{ aktif: sekme === 'otel' }"
          @click="sekme = 'otel'"
        >
          <span class="sekme-no">3</span>
          Konaklama
        </button>
      </nav>

      <!-- 5. Hafta: Şehir önerileri -->
      <div v-if="sekme === 'sehir'" class="detail-service">
        <div class="service-heading">
          <div>
            <span class="service-eyebrow">ÖNERİLER</span>
            <h3>Sana uygun şehirler</h3>
            <p>
              Toplam maliyeti, kalan bütçeyi ve ilgi alanlarına uyumu karşılaştır.
            </p>
          </div>

          <span class="service-mark" aria-hidden="true">★</span>
        </div>

        <div class="service-content">
          <SehirOnerileri
            :key="seyahat.id"
            :trip-id="seyahat.id"
            :is-owner="seyahat.role === 'owner'"
            @secildi="secimSonrasiYenile"
          />
        </div>
      </div>

      <!-- Şehir seçilmeden uçuş/otel aranamaz -->
      <div
        v-if="(sekme === 'ucus' || sekme === 'otel') && !seyahat.selected_destination_id"
        class="sekme-uyari"
      >
        <p>Uçuş ve otel aramak için önce bir şehir seçmelisin.</p>
        <button type="button" class="v-buton" @click="sekme = 'sehir'">Şehir seç</button>
      </div>

      <!-- Uçuşlar -->
      <div v-if="sekme === 'ucus' && seyahat.selected_destination_id" class="detail-service">
        <div class="service-heading">
          <div>
            <span class="service-eyebrow">YOLCULUK</span>
            <h3>Uçuş seçenekleri</h3>
            <p>
              Uygun uçuşları incele ve seyahat planına ekle.
            </p>
          </div>

          <span class="service-mark" aria-hidden="true">✈</span>
        </div>

        <div class="service-content">
          <UcusSonuclari
            :key="`${seyahat.id}-${seyahat.selected_destination_id}`"
            :trip-id="seyahat.id"
            :destination-id="seyahat.selected_destination_id"
            :origin-airport="seyahat.origin_airport_code"
            :start-date="seyahat.start_date"
            :end-date="seyahat.end_date"
          />
        </div>
      </div>

      <!-- Oteller -->
      <div v-if="sekme === 'otel' && seyahat.selected_destination_id" class="detail-service">
        <div class="service-heading hotel-heading">
          <div>
            <span class="service-eyebrow">KONAKLAMA</span>
            <h3>Konaklama seçenekleri</h3>
            <p>
              Otelleri karşılaştır ve beğendiğini planına kaydet.
            </p>
          </div>

          <span class="service-mark" aria-hidden="true">⌂</span>
        </div>

        <div class="service-content">
          <OtelSonuclari
            :key="`${seyahat.id}-${seyahat.selected_destination_id}`"
            :trip-id="seyahat.id"
            :destination-id="seyahat.selected_destination_id"
            :destination="seyahat.destination"
            :check-in="seyahat.start_date"
            :check-out="seyahat.end_date"
            :adults="seyahat.people_count"
          />
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.trip-detail {
  --ink: #293042;
  --muted: #778197;

  width: 100%;
  min-width: 0;
  padding: 14px 0 8px;
  color: var(--ink);
  font-family:
    "Nunito Sans",
    "Segoe UI",
    system-ui,
    sans-serif;
}

.detail-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 15px;
  margin-bottom: 20px;
}

.topbar-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  font-weight: 750;
}

.topbar-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #a999d5;
}

.close-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 14px;
  border: 1px solid #e0deeb;
  border-radius: 10px;
  background: white;
  color: #69728a;
  font-size: 13px;
  font-weight: 650;
  cursor: pointer;
}

.close-button span {
  font-size: 19px;
  line-height: 1;
}

.close-button:hover {
  background: #f4f1fa;
}

.detail-state {
  padding: 25px;
  border-radius: 14px;
  background: #f1f4fb;
  color: #687590;
}

.error-state {
  background: #fff1f4;
  color: #b45f7b;
}

/* Seyahat özeti */
.detail-overview {
  position: relative;
  overflow: hidden;
  min-height: 260px;
  padding: 34px clamp(22px, 4vw, 48px);
  border: 1px solid #e4e0f1;
  border-radius: 22px;
  background: linear-gradient(
    110deg,
    #e7effd,
    #f0e9fa 60%,
    #f9e4ed
  );
}

.overview-main {
  position: relative;
  z-index: 2;
}

.overview-eyebrow {
  color: #7785b8;
  font-size: 10px;
  font-weight: 750;
  letter-spacing: 1.7px;
}

.overview-main h2 {
  margin: 10px 0 25px;
  font-size: clamp(23px, 3vw, 34px);
  font-weight: 750;
  letter-spacing: -0.8px;
  overflow-wrap: anywhere;
}

.overview-route {
  display: flex;
  align-items: center;
  gap: 25px;
  max-width: 610px;
}

.route-place {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 100px;
}

.route-caption {
  color: #8c89ab;
  font-size: 10px;
  font-weight: 750;
  letter-spacing: 1.3px;
}

.route-place strong {
  font-size: clamp(16px, 2vw, 22px);
  font-weight: 750;
}

.route-place > span:last-child {
  color: #778197;
  font-size: 12px;
}

.route-line {
  display: flex;
  align-items: center;
  flex: 1;
  gap: 6px;
  color: #8e89c4;
}

.route-circle {
  width: 7px;
  height: 7px;
  flex-shrink: 0;
  border: 1.5px solid currentColor;
  border-radius: 50%;
}

.route-dashes {
  flex: 1;
  border-top: 1.5px dashed currentColor;
}

.route-plane {
  font-size: 24px;
}

.overview-dates {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 13px;
  margin-top: 26px;
  color: #4c6089;
  font-size: 13px;
  font-weight: 650;
}

.night-badge {
  padding: 6px 11px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.65);
  color: #8575b4;
  font-size: 12px;
}

.overview-decoration {
  position: absolute;
  inset: 0 0 0 auto;
  width: 36%;
  overflow: hidden;
  pointer-events: none;
}

.decoration-sun {
  position: absolute;
  right: 20%;
  top: 30px;
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: #f5ccdb;
}

.decoration-hill {
  position: absolute;
  right: -25%;
  bottom: -115px;
  width: 130%;
  height: 190px;
  border-radius: 50% 50% 0 0;
}

.hill-back {
  transform: rotate(-12deg);
  background: #c6b8e7;
}

.hill-front {
  bottom: -130px;
  transform: rotate(10deg);
  background: #aac1e9;
}

/* Bilgi şeridi */
.detail-facts {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-top: 18px;
}

.fact {
  display: flex;
  align-items: center;
  gap: 13px;
  min-width: 0;
  padding: 17px;
  border: 1px solid #e7e8f0;
  border-radius: 15px;
  background: white;
}

.fact-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 39px;
  height: 39px;
  border-radius: 12px;
  font-size: 19px;
  font-weight: 750;
}

.fact-blue {
  background: #e7effc;
  color: #6d8dc5;
}

.fact-lilac {
  background: #eee8fa;
  color: #967ec6;
}

.fact-pink {
  background: #fae9f0;
  color: #c083a2;
}

.fact > div {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}

.fact-label {
  color: var(--muted);
  font-size: 11px;
}

.fact strong {
  font-size: 13px;
  font-weight: 750;
  overflow-wrap: anywhere;
}

.detail-role {
  margin: 15px 0 35px;
  color: #7a8499;
  font-size: 12px;
}

.detail-role strong {
  color: #8d79b9;
}

/* Uçuş ve otel bölümleri */
.detail-service {
  margin-top: 28px;
  overflow: hidden;
  border: 1px solid #e5e7f0;
  border-radius: 20px;
  background: white;
}

.service-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 25px 30px;
  background: linear-gradient(
    100deg,
    #eaf1fd,
    #f3f0fc
  );
}

.hotel-heading {
  background: linear-gradient(
    100deg,
    #f5ecf8,
    #fcecf2
  );
}

.service-eyebrow {
  color: #8d83b8;
  font-size: 10px;
  font-weight: 750;
  letter-spacing: 1.5px;
}

.service-heading h3 {
  margin-top: 7px;
  font-size: 22px;
  font-weight: 750;
  letter-spacing: -0.5px;
}

.service-heading p {
  margin-top: 7px;
  color: #7a8399;
  font-size: 13px;
}

.service-mark {
  color: #9a91c9;
  font-size: 35px;
}

.service-content {
  padding: 10px;
  min-width: 0;
}

@media (max-width: 1000px) {
  .detail-facts {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .detail-overview {
    padding: 25px 20px;
  }

  .overview-decoration {
    opacity: 0.25;
    width: 60%;
  }

  .overview-route {
    gap: 10px;
  }

  .route-place {
    min-width: 0;
  }

  .route-line {
    gap: 3px;
  }

  .detail-facts {
    grid-template-columns: 1fr;
  }

  .service-heading {
    padding: 22px;
  }

  .service-content {
    padding: 0;
  }
}

/* ---------- Sekmeler ---------- */
.sekmeler {
  display: flex;
  gap: 6px;
  margin: 26px 0 18px;
  padding: 6px;
  overflow-x: auto;
  border: 1px solid #eeecf4;
  border-radius: 18px;
  background: white;
}

.sekme {
  display: inline-flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 12px 16px;
  border: 0;
  border-radius: 13px;
  background: transparent;
  color: var(--v-muted);
  font: inherit;
  font-size: 15px;
  font-weight: 800;
  white-space: nowrap;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
}

.sekme:hover {
  background: var(--v-surface-soft);
  color: var(--v-ink);
}

.sekme.aktif {
  background: var(--v-gradient-button);
  box-shadow: 0 8px 18px rgba(133, 114, 183, 0.22);
  color: white;
}

.sekme-no {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(133, 114, 183, 0.15);
  font-size: 12px;
}

.sekme.aktif .sekme-no {
  background: rgba(255, 255, 255, 0.3);
}

.sekme-uyari {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 22px 24px;
  border: 1px dashed #d9d1ee;
  border-radius: 20px;
  background: #faf8fe;
}

.sekme-uyari p {
  margin: 0;
  color: var(--v-muted);
}
</style>
