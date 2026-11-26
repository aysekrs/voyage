
<script setup lang="ts">
import { ref, computed } from 'vue'

interface Otel {
  hotel_name: string
  stars: number
  total_price: number
  nightly_price: number
  currency: string
  image_url: string | null
}

interface ApiOtel {
  hotel_name?: string
  stars?: number | string
  total_price?: number | string
  nightly_price?: number | string
  currency?: string
  image_url?: string | null
}

const props = defineProps<{
  tripId?: number | null
  destinationId?: number | null
  destination?: string | null
  checkIn?: string | null
  checkOut?: string | null
  adults?: number | null
}>()

const sehir = ref(props.destination || '')
const giris = ref(props.checkIn?.slice(0, 10) || '')
const cikis = ref(props.checkOut?.slice(0, 10) || '')
const yetiskin = ref(props.adults ?? 2)

const oteller = ref<Otel[]>([])
const siralama = ref('varsayilan')
const yildizFiltresi = ref(0)
const yukleniyor = ref(false)
const hata = ref('')
const veriKaynagi = ref('')
const kaydediliyor = ref<string | null>(null)
const kayitMesajlari = ref<Record<string, { text: string, success: boolean }>>({})

const geceSayisi = computed(() => {
  if (!giris.value || !cikis.value) return 0
  const baslangic = Date.parse(`${giris.value}T00:00:00Z`)
  const bitis = Date.parse(`${cikis.value}T00:00:00Z`)
  if (!Number.isFinite(baslangic) || !Number.isFinite(bitis)) return 0
  return Math.max(0, Math.round((bitis - baslangic) / 86400000))
})

const siraliOteller = computed(() => {
  let liste = [...oteller.value]

  if (yildizFiltresi.value > 0) {
    liste = liste.filter(otel => otel.stars === yildizFiltresi.value)
  }

  if (siralama.value === 'artan') {
    liste.sort((a, b) => a.total_price - b.total_price)
  }

  if (siralama.value === 'azalan') {
    liste.sort((a, b) => b.total_price - a.total_price)
  }

  return liste
})

async function otelAra() {
  yukleniyor.value = true
  hata.value = ''
  oteller.value = []
  veriKaynagi.value = ''
  kayitMesajlari.value = {}
  siralama.value = 'varsayilan'
  yildizFiltresi.value = 0

  try {
    if (!sehir.value.trim()) {
      throw new Error('Lütfen şehir girin.')
    }

    if (!giris.value || !cikis.value || cikis.value <= giris.value) {
      throw new Error('Çıkış tarihi giriş tarihinden sonra olmalıdır.')
    }

    if (!Number.isInteger(yetiskin.value) || yetiskin.value < 1 || yetiskin.value > 20) {
      throw new Error('Yetişkin sayısı 1 ile 20 arasında olmalıdır.')
    }

    const params = new URLSearchParams({
      destination: sehir.value.trim(),
      check_in: giris.value,
      check_out: cikis.value,
      adults: String(yetiskin.value)
    })

    const response = await fetch(
      `http://localhost:8000/external/hotels/real?${params}`
    )

    if (!response.ok) {
      throw new Error('Otel bilgileri alınamadı.')
    }

    const data = await response.json()
    veriKaynagi.value = data.data_source || ''

    oteller.value = (data.hotels || []).map((otel: ApiOtel) => {
      const toplam = Number(
        otel.total_price ??
        Number(otel.nightly_price || 0) * geceSayisi.value
      )

      return {
        hotel_name: otel.hotel_name || 'İsimsiz otel',
        stars: Number(otel.stars || 0),
        total_price: toplam,
        nightly_price: Number(
          otel.nightly_price ?? toplam / geceSayisi.value
        ),
        currency: otel.currency || 'TRY',
        image_url: otel.image_url || null
      }
    })

    if (!oteller.value.length) {
      hata.value = 'Uygun otel bulunamadı.'
    }
  } catch (error) {
    hata.value = error instanceof Error
      ? error.message
      : 'Otel araması sırasında hata oluştu.'
  } finally {
    yukleniyor.value = false
  }
}

function otelAnahtari(otel: Otel): string {
  return `${otel.hotel_name}|${otel.stars}|${otel.nightly_price}|${otel.currency}`
}

async function otelKaydet(otel: Otel) {
  const anahtar = otelAnahtari(otel)
  if (kaydediliyor.value) return

  if (!props.tripId || !props.destinationId) {
    kayitMesajlari.value[anahtar] = {
      text: 'Seyahat veya şehir ID bilgisi eksik. Kaydedilemedi.',
      success: false
    }
    return
  }

  if (veriKaynagi.value !== 'real' && veriKaynagi.value !== 'mock') {
    kayitMesajlari.value[anahtar] = {
      text: 'Otel verisinin kaynağı bilinmiyor. Kaydedilemedi.',
      success: false
    }
    return
  }

  kaydediliyor.value = anahtar
  delete kayitMesajlari.value[anahtar]

  try {
    const response = await fetch(
      `/api/trips/${props.tripId}/accommodations`,
      {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          destination_id: props.destinationId,
          hotel_name: otel.hotel_name,
          stars: otel.stars || null,
          nightly_price: otel.nightly_price,
          currency: otel.currency,
          data_source: veriKaynagi.value
        })
      }
    )

    if (!response.ok) {
      const details = await response.json().catch(() => null)
      const detailText = typeof details?.detail === 'string'
        ? details.detail
        : ''
      throw new Error(
        detailText || `Otel kaydedilemedi (${response.status}).`
      )
    }

    kayitMesajlari.value[anahtar] = {
      text: 'Otel seyahate kaydedildi. Bu bir rezervasyon değildir.',
      success: true
    }
  } catch (error) {
    kayitMesajlari.value[anahtar] = {
      text: error instanceof Error
        ? error.message
        : 'Otel kaydedilemedi.',
      success: false
    }
  } finally {
    kaydediliyor.value = null
  }
}

function fiyatFormatla(fiyat: number, paraBirimi: string) {
  if (!Number.isFinite(fiyat)) return 'Belirtilmedi'

  try {
    return new Intl.NumberFormat('tr-TR', {
      style: 'currency',
      currency: paraBirimi || 'TRY'
    }).format(fiyat)
  } catch {
    return `${fiyat.toLocaleString('tr-TR')} ${paraBirimi}`
  }
}
</script>

<template>
  <section class="hotel-search">
    <div class="hotel-header">
      <span class="eyebrow">KONAKLAMA SEÇENEKLERİ</span>
      <h2>Kalacak güzel bir yer bul <span>⌂</span></h2>
      <p>Gideceğin şehirdeki otelleri keşfet, karşılaştır ve seyahat planına ekle.</p>
    </div>

    <div class="search-panel">
      <div class="search-grid">
        <label class="field">
          <span>Gidilecek şehir</span>
          <input v-model="sehir" placeholder="Örn. Antalya" />
        </label>

        <label class="field">
          <span>Giriş tarihi</span>
          <input v-model="giris" type="date" />
        </label>

        <label class="field">
          <span>Çıkış tarihi</span>
          <input v-model="cikis" type="date" :min="giris" />
        </label>

        <label class="field">
          <span>Yetişkin sayısı</span>
          <input
            v-model.number="yetiskin"
            type="number"
            min="1"
            max="20"
          />
        </label>
      </div>

      <div class="search-footer">
        <div class="stay-summary">
          <span v-if="geceSayisi > 0">{{ geceSayisi }} gece konaklama</span>
          <span v-else>Konaklama tarihlerini seç</span>
        </div>

        <button
          type="button"
          class="search-button"
          :disabled="yukleniyor"
          @click="otelAra"
        >
          {{ yukleniyor ? 'Oteller aranıyor...' : 'Otelleri listele' }}
          <span aria-hidden="true">↗</span>
        </button>
      </div>
    </div>

    <p v-if="yukleniyor" class="message info">
      Konaklama seçenekleri yükleniyor...
    </p>

    <p v-if="hata" class="message error">{{ hata }}</p>

    <p v-if="veriKaynagi === 'mock'" class="message warning">
      Gerçek otel verilerine ulaşılamadı. API'nin örnek sonuçları gösteriliyor.
    </p>

    <div v-if="oteller.length" class="filters">
      <div class="filters-title">Sonuçları düzenle</div>

      <label>
        Fiyata göre
        <select v-model="siralama">
          <option value="varsayilan">Varsayılan</option>
          <option value="artan">En ucuzdan en pahalıya</option>
          <option value="azalan">En pahalıdan en ucuza</option>
        </select>
      </label>

      <label>
        Otel yıldızı
        <select v-model.number="yildizFiltresi">
          <option :value="0">Tüm oteller</option>
          <option :value="3">3 yıldız</option>
          <option :value="4">4 yıldız</option>
          <option :value="5">5 yıldız</option>
        </select>
      </label>
    </div>

    <div v-if="oteller.length" class="results-heading">
      <div>
        <span class="eyebrow">SENİN İÇİN SEÇENEKLER</span>
        <h3>{{ sehir }} otelleri</h3>
      </div>
      <span class="result-count">{{ siraliOteller.length }} otel</span>
    </div>

    <p
      v-if="oteller.length && !siraliOteller.length"
      class="message warning"
    >
      Seçilen yıldız sayısına uygun otel bulunamadı.
    </p>

    <div v-if="siraliOteller.length" class="hotel-list">
      <article
        v-for="(otel, index) in siraliOteller"
        :key="index"
        class="hotel-card"
      >
        <div class="hotel-image">
          <img
            v-if="otel.image_url"
            :src="otel.image_url"
            :alt="otel.hotel_name"
            loading="lazy"
          />
          <div v-else class="image-placeholder">
            <span class="placeholder-icon">⌂</span>
            <span>Konaklama</span>
          </div>
        </div>

        <div class="hotel-details">
          <div class="hotel-info">
            <span class="hotel-location">{{ sehir }}</span>
            <h4>{{ otel.hotel_name }}</h4>

            <div class="hotel-rating">
              <span v-if="otel.stars > 0" class="stars">
                {{ '★'.repeat(Math.min(5, Math.max(0, Math.floor(otel.stars)))) }}
              </span>
              <span v-else class="no-rating">Yıldız bilgisi yok</span>
              <span v-if="otel.stars > 0" class="star-label">
                {{ otel.stars }} yıldızlı otel
              </span>
            </div>

            <div class="hotel-meta">
              <span>{{ geceSayisi }} gece</span>
              <span>{{ yetiskin }} yetişkin</span>
            </div>

            <p class="nightly-price">
              Gecelik
              <strong>{{ fiyatFormatla(otel.nightly_price, otel.currency) }}</strong>
            </p>
          </div>

          <div class="hotel-booking">
            <span class="price-label">Toplam konaklama</span>
            <strong class="total-price">
              {{ fiyatFormatla(otel.total_price, otel.currency) }}
            </strong>
            <span class="price-note">{{ geceSayisi }} gece için</span>

            <button
              type="button"
              :disabled="!!kaydediliyor || !tripId || !destinationId"
              @click="otelKaydet(otel)"
            >
              {{
                kaydediliyor === otelAnahtari(otel)
                  ? 'Kaydediliyor...'
                  : 'Oteli kaydet'
              }}
            </button>
          </div>

          <div
            v-if="!tripId || !destinationId || kayitMesajlari[otelAnahtari(otel)]"
            class="hotel-notice"
          >
            <p v-if="!tripId || !destinationId" class="notice-warning">
              Otel kaydetmek için seyahat ve şehir bilgisi gerekli.
            </p>
            <p
              v-if="kayitMesajlari[otelAnahtari(otel)]"
              :class="kayitMesajlari[otelAnahtari(otel)]?.success ? 'notice-success' : 'notice-error'"
            >
              {{ kayitMesajlari[otelAnahtari(otel)]?.text }}
            </p>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.hotel-search {
  width: 100%;
  min-width: 0;
  padding: 12px 4px 28px;
  color: #30364a;
  font-family: "Nunito Sans", "Segoe UI", system-ui, sans-serif;
}

.hotel-header {
  padding: 18px 8px 25px;
}

.eyebrow {
  color: #9886c1;
  font-size: 11px;
  font-weight: 750;
  letter-spacing: 1.5px;
}

.hotel-header h2 {
  margin-top: 9px;
  font-size: clamp(26px, 3vw, 35px);
  font-weight: 750;
  letter-spacing: -1px;
}

.hotel-header h2 span {
  color: #b29bd2;
}

.hotel-header p {
  margin-top: 9px;
  color: #7a8499;
  font-size: 14px;
  line-height: 1.6;
}

.search-panel {
  padding: 25px;
  border: 1px solid #e8e3f0;
  border-radius: 20px;
  background: linear-gradient(120deg, #f7f5fd, #fdf5f8);
}

.search-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 9px;
  min-width: 0;
}

.field span {
  color: #707a90;
  font-size: 12px;
  font-weight: 650;
}

.field input {
  width: 100%;
  min-width: 0;
  padding: 13px 14px;
  border: 1px solid #e1e3ef;
  border-radius: 12px;
  outline: none;
  background: white;
  color: #30364a;
  font-size: 14px;
}

.field input:focus {
  border-color: #b49bd5;
  box-shadow: 0 0 0 3px #b49bd522;
}

.search-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 18px;
  margin-top: 24px;
}

.stay-summary {
  padding: 9px 13px;
  border-radius: 25px;
  background: #eee9f8;
  color: #8876b3;
  font-size: 12px;
  font-weight: 650;
}

.search-button {
  display: flex;
  align-items: center;
  gap: 22px;
  padding: 13px 22px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(110deg, #849ed7, #b09ad3);
  color: white;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.search-button span {
  font-size: 18px;
}

.search-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.message {
  margin-top: 15px;
  padding: 13px 17px;
  border-radius: 11px;
  font-size: 13px;
  line-height: 1.6;
}

.message.error {
  background: #fff0f4;
  color: #b35f7c;
}

.message.warning {
  background: #fff6e9;
  color: #a67b43;
}

.message.info {
  background: #edf3fc;
  color: #6381b4;
}

.filters {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 15px 25px;
  margin-top: 28px;
  padding: 19px 22px;
  border: 1px solid #e7e7f0;
  border-radius: 15px;
  background: #fafbfe;
}

.filters-title {
  margin-right: auto;
  color: #39445e;
  font-size: 14px;
  font-weight: 750;
}

.filters label {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #788298;
  font-size: 12px;
}

.filters select {
  max-width: 230px;
  padding: 9px 12px;
  border: 1px solid #e1e3ed;
  border-radius: 9px;
  background: white;
  color: #46516b;
  font-size: 12px;
}

.results-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 15px;
  margin: 32px 4px 19px;
}

.results-heading h3 {
  margin-top: 6px;
  font-size: 23px;
  font-weight: 750;
  letter-spacing: -0.5px;
}

.result-count {
  color: #9889c1;
  font-size: 12px;
}

.hotel-list {
  display: grid;
  gap: 17px;
}

.hotel-card {
  display: grid;
  grid-template-columns: 210px minmax(0, 1fr);
  gap: 0;
  overflow: hidden;
  border: 1px solid #e5e7f0;
  border-radius: 18px;
  background: white;
  box-shadow: 0 5px 20px #53618c09;
}

.hotel-card:hover {
  border-color: #d0c5e5;
  box-shadow: 0 8px 25px #53618c12;
}

.hotel-image {
  min-height: 210px;
  overflow: hidden;
  background: #eee9f6;
}

.hotel-image img {
  width: 100%;
  height: 100%;
  min-height: 210px;
  object-fit: cover;
}

.image-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  width: 100%;
  height: 100%;
  min-height: 210px;
  background: linear-gradient(140deg, #e4edfa, #eee5f7, #f8e5ee);
  color: #a28ec3;
  font-size: 12px;
}

.placeholder-icon {
  font-size: 65px;
  font-weight: 300;
}

.hotel-details {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 190px;
  gap: 20px;
  min-width: 0;
  padding: 24px;
}

.hotel-info {
  min-width: 0;
}

.hotel-location {
  color: #9b89c1;
  font-size: 11px;
  font-weight: 700;
}

.hotel-info h4 {
  margin-top: 7px;
  color: #30394e;
  font-size: 20px;
  font-weight: 750;
  letter-spacing: -0.4px;
  overflow-wrap: anywhere;
}

.hotel-rating {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 9px;
  margin-top: 12px;
}

.stars {
  color: #e0b774;
  font-size: 17px;
  letter-spacing: 2px;
}

.star-label,
.no-rating {
  color: #8d96a7;
  font-size: 11px;
}

.hotel-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
  margin-top: 17px;
}

.hotel-meta span {
  padding: 7px 11px;
  border-radius: 20px;
  background: #f2f3f9;
  color: #75829b;
  font-size: 11px;
}

.nightly-price {
  margin-top: 18px;
  color: #8d96a7;
  font-size: 12px;
}

.nightly-price strong {
  margin-left: 5px;
  color: #5e6d8d;
  font-size: 13px;
}

.hotel-booking {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  justify-content: center;
  gap: 9px;
  padding-left: 20px;
  border-left: 1px solid #ececf3;
  text-align: right;
}

.price-label {
  color: #929bad;
  font-size: 11px;
}

.total-price {
  color: #7488be;
  font-size: 22px;
  font-weight: 750;
  overflow-wrap: anywhere;
}

.price-note {
  color: #a0a6b5;
  font-size: 11px;
}

.hotel-booking button {
  width: 100%;
  margin-top: 9px;
  padding: 12px 15px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(110deg, #849ed7, #a393d1);
  color: white;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.hotel-booking button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.hotel-notice {
  grid-column: 1 / -1;
  font-size: 12px;
}

.hotel-notice p {
  padding: 10px 12px;
  border-radius: 9px;
}

.notice-warning {
  background: #fff6e9;
  color: #a67b43;
}

.notice-success {
  background: #eef8f3;
  color: #43876c;
}

.notice-error {
  background: #fff0f4;
  color: #b35f7c;
}

@media (max-width: 1050px) {
  .search-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .hotel-card {
    grid-template-columns: 170px minmax(0, 1fr);
  }

  .hotel-details {
    grid-template-columns: 1fr;
  }

  .hotel-booking {
    align-items: flex-start;
    padding: 16px 0 0;
    border-top: 1px solid #ececf3;
    border-left: none;
    text-align: left;
  }

  .hotel-booking button {
    width: auto;
  }
}

@media (max-width: 680px) {
  .search-panel {
    padding: 18px;
  }

  .search-grid {
    grid-template-columns: 1fr;
  }

  .search-button {
    justify-content: center;
    width: 100%;
  }

  .filters {
    align-items: stretch;
    flex-direction: column;
  }

  .filters label {
    justify-content: space-between;
  }

  .hotel-card {
    grid-template-columns: 1fr;
  }

  .hotel-image,
  .hotel-image img,
  .image-placeholder {
    min-height: 190px;
    max-height: 240px;
  }

  .hotel-details {
    padding: 19px;
  }

  .hotel-booking button {
    width: 100%;
  }
}
</style>
