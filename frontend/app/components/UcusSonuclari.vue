
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

interface Ucus {
  price: string
  priceValue: number
  origin: string
  destination: string
  departure: string
  arrival: string
  stops: number | null
  airline: string | null
  currency: string | null
}

interface ApiUcus {
  price?: string | number
  price_per_person?: string | number
  currency?: string
  origin?: string
  destination?: string
  from_airport?: string
  to_airport?: string
  departure?: string
  arrival?: string
  departure_time?: string
  arrival_time?: string
  stops?: number | null
  airline?: string | null
}

const props = defineProps<{
  originAirport?: string | null
  startDate?: string | null
  endDate?: string | null
  tripId: number
  destinationId?: number | null
}>()

const kalkis = ref(props.originAirport || '')
const varis = ref('')
const varisNotu = ref('')

// Varış havalimanını seçilen şehirden otomatik doldur.
// Şehrin havalimanı yoksa (Versay, Brugge, Zermatt...) backend en yakın havalimanını verir.
onMounted(async () => {
  if (!props.destinationId || varis.value) return
  try {
    const sehir = await $fetch<{
      name: string
      airport_code: string | null
      airport_city: string | null
      airport_distance_km: number | null
    }>(`http://localhost:8000/destinations/${props.destinationId}`)
    if (!sehir.airport_code) {
      varisNotu.value = `${sehir.name} için havalimanı bulunamadı, kodu elle gir.`
      return
    }
    varis.value = sehir.airport_code
    if (sehir.airport_city && sehir.airport_city !== sehir.name) {
      varisNotu.value = `${sehir.name} şehrinde havalimanı yok; en yakın: ${sehir.airport_city} (${sehir.airport_code}, ~${sehir.airport_distance_km} km)`
    }
  } catch {
    // Şehir bilgisi alınamazsa kullanıcı kodu elle girebilir.
  }
})
const tarih = ref(props.startDate?.slice(0, 10) || '')
const donusTarihi = ref(props.endDate?.slice(0, 10) || '')
const yolculukTipi = ref<'tek' | 'gidisDonus'>('gidisDonus')
const testModu = ref(true)

const gidisUcuslari = ref<Ucus[]>([])
const donusUcuslari = ref<Ucus[]>([])
const yukleniyor = ref(false)
const hata = ref('')
const gidisHatasi = ref('')
const donusHatasi = ref('')
const gidisKaynagi = ref('')
const donusKaynagi = ref('')
const kaydediliyor = ref('')
const kayitMesaji = ref('')
const kayitHatasi = ref('')
const siralama = ref('varsayilan')
const aktarmaFiltresi = ref('tumu')

function fiyatSayiyaCevir(fiyat: string | number): number {
  if (typeof fiyat === 'number') return fiyat

  const temiz = String(fiyat).replace(/[^\d.,]/g, '')
  if (!temiz) return 0

  if (temiz.includes('.') && temiz.includes(',')) {
    const sonNokta = temiz.lastIndexOf('.')
    const sonVirgul = temiz.lastIndexOf(',')

    if (sonVirgul > sonNokta) {
      return Number(
        temiz.replace(/\./g, '').replace(',', '.')
      ) || 0
    }

    return Number(temiz.replace(/,/g, '')) || 0
  }

  if (/^\d{1,3}([.,]\d{3})+$/.test(temiz)) {
    return Number(temiz.replace(/[.,]/g, ''))
  }

  return Number(temiz.replace(',', '.')) || 0
}

function tarihFormatla(deger: string): string {
  if (!deger) return 'Belirtilmedi'

  const [tarihKismi, saatKismi] = deger.split('T')
  const parcalar = tarihKismi.split('-')

  if (parcalar.length !== 3) return deger

  const [yil, ay, gun] = parcalar
  const saat = saatKismi?.slice(0, 5) || ''

  return `${gun}.${ay}.${yil}${saat ? ' ' + saat : ''}`
}

function ucuslariDuzenle(
  liste: ApiUcus[],
  origin: string,
  destination: string
): Ucus[] {
  return liste.map((ucus) => {
    const fiyat = ucus.price ?? ucus.price_per_person ?? 0

    return {
      price: typeof fiyat === 'number'
        ? new Intl.NumberFormat('tr-TR', {
            style: 'currency',
            currency: ucus.currency || 'TRY'
          }).format(fiyat)
        : String(fiyat),
      priceValue: fiyatSayiyaCevir(fiyat),
      origin: ucus.origin || ucus.from_airport || origin,
      destination: ucus.destination || ucus.to_airport || destination,
      departure: ucus.departure || ucus.departure_time || '',
      arrival: ucus.arrival || ucus.arrival_time || '',
      stops: ucus.stops == null ? null : Number(ucus.stops),
      airline: ucus.airline || null,
      currency: ucus.currency || (
        typeof fiyat === 'string'
          ? fiyat.includes('₺') || fiyat.includes('TL')
            ? 'TRY'
            : fiyat.includes('€')
              ? 'EUR'
              : fiyat.includes('$')
                ? 'USD'
                : null
          : 'TRY'
      )
    }
  })
}

function ornekUcuslar(
  origin: string,
  destination: string,
  flightDate: string
): Ucus[] {
  const fiyatlar = [2753, 3806, 3240]
  const saatler = [
    ['08:00', '09:20'],
    ['12:30', '14:00'],
    ['17:15', '20:45']
  ]
  const aktarmalar = [0, 0, 1]

  return fiyatlar.map((fiyat, index) => ({
    price: new Intl.NumberFormat('tr-TR', {
      style: 'currency',
      currency: 'TRY'
    }).format(fiyat),
    priceValue: fiyat,
    origin,
    destination,
    departure: `${flightDate}T${saatler[index][0]}:00`,
    arrival: `${flightDate}T${saatler[index][1]}:00`,
    stops: aktarmalar[index],
    airline: null,
    currency: 'TRY'
  }))
}

function filtrele(liste: Ucus[]): Ucus[] {
  let sonuc = [...liste]

  if (aktarmaFiltresi.value === 'aktarmasiz') {
    sonuc = sonuc.filter(ucus => ucus.stops === 0)
  }

  if (aktarmaFiltresi.value === 'aktarmali') {
    sonuc = sonuc.filter(
      ucus => ucus.stops !== null && ucus.stops > 0
    )
  }

  if (siralama.value === 'artan') {
    sonuc.sort((a, b) => a.priceValue - b.priceValue)
  }

  if (siralama.value === 'azalan') {
    sonuc.sort((a, b) => b.priceValue - a.priceValue)
  }

  return sonuc
}

const filtreliGidis = computed(() => filtrele(gidisUcuslari.value))
const filtreliDonus = computed(() => filtrele(donusUcuslari.value))

async function ucusGetir(
  origin: string,
  destination: string,
  flightDate: string
): Promise<{ flights: Ucus[], source: string }> {
  if (testModu.value) {
    return {
      flights: ornekUcuslar(origin, destination, flightDate),
      source: 'test'
    }
  }

  const params = new URLSearchParams({
    origin,
    destination,
    date: flightDate
  })

  const response = await fetch(
    `http://localhost:8000/external/flights/real?${params}`
  )

  if (!response.ok) {
    throw new Error(`Uçuş servisi hata verdi (${response.status}).`)
  }

  const data = await response.json()

  return {
    flights: ucuslariDuzenle(
      data.flights || [],
      origin,
      destination
    ),
    source: data.data_source || ''
  }
}

async function ucusAra() {
  hata.value = ''
  gidisHatasi.value = ''
  donusHatasi.value = ''
  kayitMesaji.value = ''
  kayitHatasi.value = ''
  gidisUcuslari.value = []
  donusUcuslari.value = []
  gidisKaynagi.value = ''
  donusKaynagi.value = ''

  const origin = kalkis.value.trim().toUpperCase()
  const destination = varis.value.trim().toUpperCase()

  if (
    !/^[A-Z]{3}$/.test(origin) ||
    !/^[A-Z]{3}$/.test(destination)
  ) {
    hata.value = 'Geçerli üç harfli havalimanı kodları girin.'
    return
  }

  if (origin === destination) {
    hata.value = 'Kalkış ve varış havalimanları aynı olamaz.'
    return
  }

  if (!tarih.value) {
    hata.value = 'Lütfen gidiş tarihini seçin.'
    return
  }

  if (yolculukTipi.value === 'gidisDonus') {
    if (!donusTarihi.value) {
      hata.value = 'Lütfen dönüş tarihini seçin.'
      return
    }

    if (donusTarihi.value < tarih.value) {
      hata.value = 'Dönüş tarihi gidiş tarihinden önce olamaz.'
      return
    }
  }

  yukleniyor.value = true
  siralama.value = 'varsayilan'
  aktarmaFiltresi.value = 'tumu'

  try {
    try {
      const gidis = await ucusGetir(
        origin,
        destination,
        tarih.value
      )

      gidisUcuslari.value = gidis.flights
      gidisKaynagi.value = gidis.source

      if (!gidis.flights.length) {
        gidisHatasi.value = 'Gidiş uçuşu bulunamadı.'
      }
    } catch (error) {
      gidisHatasi.value = error instanceof Error
        ? error.message
        : 'Gidiş uçuşları alınamadı.'
    }

    if (yolculukTipi.value === 'gidisDonus') {
      try {
        const donus = await ucusGetir(
          destination,
          origin,
          donusTarihi.value
        )

        donusUcuslari.value = donus.flights
        donusKaynagi.value = donus.source

        if (!donus.flights.length) {
          donusHatasi.value = 'Dönüş uçuşu bulunamadı.'
        }
      } catch (error) {
        donusHatasi.value = error instanceof Error
          ? error.message
          : 'Dönüş uçuşları alınamadı.'
      }
    }
  } finally {
    yukleniyor.value = false
  }
}

function ucusAnahtari(
  ucus: Ucus,
  direction: 'outbound' | 'return'
) {
  return `${direction}:${ucus.origin}:${ucus.destination}:${ucus.departure}`
}

async function ucusuKaydet(
  ucus: Ucus,
  direction: 'outbound' | 'return'
) {
  kayitMesaji.value = ''
  kayitHatasi.value = ''

  const source = direction === 'outbound'
    ? gidisKaynagi.value
    : donusKaynagi.value

  if (source === 'test' || (source !== 'real' && source !== 'mock')) {
    kayitHatasi.value =
      'Test uçuşları kaydedilemez. Önce API sonuçlarını listeleyin.'
    return
  }

  if (!props.tripId || !props.destinationId) {
    kayitHatasi.value = 'Seyahat veya şehir ID bilgisi eksik.'
    return
  }

  if (!Number.isFinite(ucus.priceValue) || ucus.priceValue <= 0) {
    kayitHatasi.value = 'Bu uçuşun geçerli fiyat bilgisi bulunamadı.'
    return
  }

  const key = ucusAnahtari(ucus, direction)
  kaydediliyor.value = key

  try {
    const response = await fetch(
      `http://localhost:8000/trips/${props.tripId}/flights`,
      {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          destination_id: props.destinationId,
          direction,
          airline: ucus.airline || null,
          from_airport: ucus.origin,
          to_airport: ucus.destination,
          departure_time: ucus.departure || null,
          arrival_time: ucus.arrival || null,
          price_per_person: ucus.priceValue,
          currency: ucus.currency || null,
          data_source: source
        })
      }
    )

    if (!response.ok) {
      const body = await response.json().catch(() => ({}))
      throw new Error(
        typeof body.detail === 'string'
          ? body.detail
          : `Kayıt başarısız (${response.status}).`
      )
    }

    kayitMesaji.value =
      `${direction === 'outbound' ? 'Gidiş' : 'Dönüş'} uçuşu seyahate kaydedildi.`
  } catch (error) {
    kayitHatasi.value = error instanceof Error
      ? error.message
      : 'Uçuş kaydedilemedi.'
  } finally {
    kaydediliyor.value = ''
  }
}
</script>

<template>
  <section class="flight-search">
    <div class="flight-header">
      <div>
        <span class="eyebrow">YOLCULUĞUNU PLANLA</span>
        <h2>Uçuşunu bul <span>✈</span></h2>
        <p>Rotana uygun uçuşları keşfet, karşılaştır ve planına ekle.</p>
      </div>
    </div>

    <div class="search-area">
      <div class="trip-type">
        <label :class="{ active: yolculukTipi === 'tek' }">
          <input v-model="yolculukTipi" type="radio" value="tek" />
          Tek yön
        </label>
        <label :class="{ active: yolculukTipi === 'gidisDonus' }">
          <input v-model="yolculukTipi" type="radio" value="gidisDonus" />
          Gidiş-dönüş
        </label>
      </div>

      <div class="search-fields">
        <label class="field">
          <span>Kalkış havalimanı</span>
          <input
            v-model="kalkis"
            maxlength="3"
            placeholder="Örn. IST"
          />
        </label>

        <label class="field">
          <span>Varış havalimanı</span>
          <input
            v-model="varis"
            maxlength="3"
            placeholder="Örn. AYT"
          />
          <small v-if="varisNotu" class="field-note">{{ varisNotu }}</small>
        </label>

        <label class="field">
          <span>Gidiş tarihi</span>
          <input v-model="tarih" type="date" />
        </label>

        <label
          v-if="yolculukTipi === 'gidisDonus'"
          class="field"
        >
          <span>Dönüş tarihi</span>
          <input
            v-model="donusTarihi"
            type="date"
            :min="tarih"
          />
        </label>
      </div>

      <div class="search-bottom">
        <label class="test-toggle">
          <input v-model="testModu" type="checkbox" />
          <span>Test modu</span>
          <small>API isteği gönderilmez</small>
        </label>

        <button
          type="button"
          class="search-button"
          :disabled="yukleniyor"
          @click="ucusAra"
        >
          {{ yukleniyor ? 'Uçuşlar aranıyor...' : 'Uçuşları listele' }}
          <span aria-hidden="true">↗</span>
        </button>
      </div>
    </div>

    <p v-if="hata" class="message error">{{ hata }}</p>
    <p v-if="kayitMesaji" class="message success">{{ kayitMesaji }}</p>
    <p v-if="kayitHatasi" class="message error">{{ kayitHatasi }}</p>

    <p v-if="yukleniyor" class="message info">
      Uçuş seçenekleri yükleniyor...
    </p>

    <p
      v-if="gidisKaynagi === 'mock' || donusKaynagi === 'mock'"
      class="message warning"
    >
      Gerçek uçuş servisine ulaşılamadı. API'nin örnek verileri gösteriliyor.
    </p>

    <p
      v-if="gidisKaynagi === 'test' || donusKaynagi === 'test'"
      class="message info"
    >
      Test modu açık. Gösterilen uçuşlar temsili verilerdir;
      gerçek API'ye istek gönderilmedi.
    </p>

    <div
      v-if="gidisUcuslari.length || donusUcuslari.length"
      class="filters"
    >
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
        Aktarma
        <select v-model="aktarmaFiltresi">
          <option value="tumu">Tüm uçuşlar</option>
          <option value="aktarmasiz">Aktarmasız</option>
          <option value="aktarmali">Aktarmalı</option>
        </select>
      </label>
    </div>

    <div
      v-if="gidisUcuslari.length || gidisHatasi"
      class="results-section"
    >
      <div class="results-heading">
        <h3>Gidiş uçuşları</h3>
        <span>{{ filtreliGidis.length }} seçenek</span>
      </div>

      <p v-if="gidisHatasi" class="message error">
        {{ gidisHatasi }}
      </p>

      <p
        v-else-if="!filtreliGidis.length"
        class="message warning"
      >
        Seçilen filtreye uygun gidiş uçuşu yok.
      </p>

      <div class="flight-list">
        <article
          v-for="(ucus, index) in filtreliGidis"
          :key="index"
          class="flight-card"
        >
          <div class="flight-main">
            <div class="flight-route">
              <div class="airport">
                <strong>{{ ucus.origin }}</strong>
                <span>Kalkış</span>
              </div>

              <div class="route-visual">
                <span class="route-line"></span>
                <span class="plane-icon">✈</span>
                <span class="route-line"></span>
              </div>

              <div class="airport">
                <strong>{{ ucus.destination }}</strong>
                <span>Varış</span>
              </div>
            </div>

            <div class="flight-times">
              <span>{{ tarihFormatla(ucus.departure) }}</span>
              <span>{{ tarihFormatla(ucus.arrival) }}</span>
            </div>

            <div class="flight-extra">
              <span v-if="ucus.airline">{{ ucus.airline }}</span>
              <span class="stops-badge">
                {{
                  ucus.stops === null
                    ? 'Aktarma bilgisi yok'
                    : ucus.stops === 0
                      ? 'Aktarmasız'
                      : `${ucus.stops} aktarma`
                }}
              </span>
            </div>
          </div>

          <div class="flight-price">
            <span>Uçuş fiyatı</span>
            <strong>{{ ucus.price }}</strong>

            <button
              v-if="gidisKaynagi === 'real' || gidisKaynagi === 'mock'"
              type="button"
              :disabled="!!kaydediliyor || !tripId || !destinationId"
              @click="ucusuKaydet(ucus, 'outbound')"
            >
              {{
                kaydediliyor === ucusAnahtari(ucus, 'outbound')
                  ? 'Kaydediliyor...'
                  : 'Uçuşu kaydet'
              }}
            </button>
          </div>
        </article>
      </div>
    </div>

    <div
      v-if="yolculukTipi === 'gidisDonus' && (donusUcuslari.length || donusHatasi)"
      class="results-section"
    >
      <div class="results-heading">
        <h3>Dönüş uçuşları</h3>
        <span>{{ filtreliDonus.length }} seçenek</span>
      </div>

      <p v-if="donusHatasi" class="message error">
        {{ donusHatasi }}
      </p>

      <p
        v-else-if="!filtreliDonus.length"
        class="message warning"
      >
        Seçilen filtreye uygun dönüş uçuşu yok.
      </p>

      <div class="flight-list">
        <article
          v-for="(ucus, index) in filtreliDonus"
          :key="index"
          class="flight-card"
        >
          <div class="flight-main">
            <div class="flight-route">
              <div class="airport">
                <strong>{{ ucus.origin }}</strong>
                <span>Kalkış</span>
              </div>

              <div class="route-visual">
                <span class="route-line"></span>
                <span class="plane-icon">✈</span>
                <span class="route-line"></span>
              </div>

              <div class="airport">
                <strong>{{ ucus.destination }}</strong>
                <span>Varış</span>
              </div>
            </div>

            <div class="flight-times">
              <span>{{ tarihFormatla(ucus.departure) }}</span>
              <span>{{ tarihFormatla(ucus.arrival) }}</span>
            </div>

            <div class="flight-extra">
              <span v-if="ucus.airline">{{ ucus.airline }}</span>
              <span class="stops-badge">
                {{
                  ucus.stops === null
                    ? 'Aktarma bilgisi yok'
                    : ucus.stops === 0
                      ? 'Aktarmasız'
                      : `${ucus.stops} aktarma`
                }}
              </span>
            </div>
          </div>

          <div class="flight-price">
            <span>Uçuş fiyatı</span>
            <strong>{{ ucus.price }}</strong>

            <button
              v-if="donusKaynagi === 'real' || donusKaynagi === 'mock'"
              type="button"
              :disabled="!!kaydediliyor || !tripId || !destinationId"
              @click="ucusuKaydet(ucus, 'return')"
            >
              {{
                kaydediliyor === ucusAnahtari(ucus, 'return')
                  ? 'Kaydediliyor...'
                  : 'Uçuşu kaydet'
              }}
            </button>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>

<style scoped>
.flight-search {
  width: 100%;
  min-width: 0;
  padding: 12px 4px 28px;
  color: #30364a;
  font-family: "Nunito Sans", "Segoe UI", sans-serif;
}

.flight-header {
  padding: 18px 8px 25px;
}

.eyebrow {
  color: #9886c1;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1.5px;
}

.flight-header h2 {
  margin-top: 9px;
  font-size: clamp(26px, 3vw, 35px);
  font-weight: 750;
  letter-spacing: -1px;
}

.flight-header h2 span {
  color: #a998d5;
}

.flight-header p {
  margin-top: 9px;
  color: #7a8499;
  font-size: 14px;
}

.search-area {
  padding: 25px;
  border: 1px solid #e6e5f0;
  border-radius: 20px;
  background: linear-gradient(120deg, #f6f8fe, #faf5fc);
}

.trip-type {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 22px;
}

.trip-type label {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 10px 16px;
  border: 1px solid #e2e1ed;
  border-radius: 30px;
  background: white;
  color: #6f788d;
  font-size: 13px;
  cursor: pointer;
}

.trip-type label.active {
  border-color: #b6a7d9;
  background: #eee9fa;
  color: #7868a8;
}

.trip-type input {
  accent-color: #9784c7;
}

.search-fields {
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
  border-color: #a996d2;
  box-shadow: 0 0 0 3px #a996d222;
}

.search-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 20px;
  margin-top: 25px;
}

.test-toggle {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 9px;
  color: #68748d;
  font-size: 13px;
  cursor: pointer;
}

.test-toggle input {
  accent-color: #9784c7;
}

.test-toggle small {
  color: #9aa2b1;
  font-size: 11px;
}

.search-button {
  display: flex;
  align-items: center;
  gap: 22px;
  padding: 13px 22px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(110deg, #779bd6, #a28ed0);
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

.message.success {
  background: #eef8f3;
  color: #43876c;
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

.results-section {
  margin-top: 35px;
}

.results-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 15px;
  margin-bottom: 17px;
}

.results-heading h3 {
  font-size: 21px;
  font-weight: 750;
  letter-spacing: -0.4px;
}

.results-heading > span {
  color: #9889c1;
  font-size: 12px;
}

.flight-list {
  display: grid;
  gap: 15px;
}

.flight-card {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 22px;
  padding: 23px;
  border: 1px solid #e5e7f0;
  border-radius: 17px;
  background: white;
  box-shadow: 0 5px 20px #53618c09;
}

.flight-card:hover {
  border-color: #cfc7e8;
  box-shadow: 0 8px 25px #53618c12;
}

.flight-main {
  flex: 1;
  min-width: 0;
}

.flight-route {
  display: flex;
  align-items: center;
  gap: 20px;
  max-width: 470px;
}

.airport {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.airport strong {
  color: #35415b;
  font-size: 25px;
  font-weight: 750;
}

.airport span {
  color: #98a0b1;
  font-size: 11px;
}

.route-visual {
  display: flex;
  align-items: center;
  flex: 1;
  gap: 7px;
  color: #a393ce;
}

.route-line {
  flex: 1;
  border-top: 1.5px dashed #c7bee0;
}

.plane-icon {
  font-size: 23px;
}

.flight-times {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 22px;
  margin-top: 17px;
  color: #727d93;
  font-size: 12px;
}

.flight-extra {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 15px;
  color: #748098;
  font-size: 12px;
}

.stops-badge {
  padding: 6px 11px;
  border-radius: 20px;
  background: #eef1fa;
  color: #7486b6;
  font-size: 11px;
  font-weight: 650;
}

.flight-price {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  justify-content: center;
  gap: 9px;
  min-width: 175px;
  padding-left: 25px;
  border-left: 1px solid #ececf3;
  text-align: right;
}

.flight-price > span {
  color: #929bad;
  font-size: 11px;
}

.flight-price strong {
  color: #697fbb;
  font-size: 23px;
  font-weight: 750;
  overflow-wrap: anywhere;
}

.flight-price button {
  margin-top: 9px;
  padding: 11px 17px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(110deg, #849ed7, #a393d1);
  color: white;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.flight-price button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 1050px) {
  .search-fields {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 680px) {
  .search-area {
    padding: 18px;
  }

  .search-fields {
    grid-template-columns: 1fr;
  }

  .search-bottom {
    align-items: stretch;
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

  .flight-card {
    flex-direction: column;
    padding: 19px;
  }

  .flight-route {
    gap: 10px;
  }

  .airport strong {
    font-size: 21px;
  }

  .flight-price {
    align-items: flex-start;
    min-width: 0;
    padding: 17px 0 0;
    border-top: 1px solid #ececf3;
    border-left: none;
    text-align: left;
  }

  .flight-price button {
    width: 100%;
  }
}
.field-note {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: var(--muted, #64748b);
}
</style>
