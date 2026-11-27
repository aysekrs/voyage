
<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

const emit = defineEmits<{ (e: 'olusturuldu', id: number): void }>()
const route = useRoute()

// Kalkış havalimanı: HavalimaniSecici (dünyadaki tarifeli havalimanları, airports tablosu)

type Agirlik =
  | 'nature_weight'
  | 'food_weight'
  | 'history_weight'
  | 'nightlife_weight'

const ilgiAlanlari: { key: Agirlik; label: string; icon: string }[] = [
  { key: 'nature_weight', label: 'Doğa', icon: '🌿' },
  { key: 'food_weight', label: 'Yeme & içme', icon: '🍝' },
  { key: 'history_weight', label: 'Kültür & tarih', icon: '🏛️' },
  { key: 'nightlife_weight', label: 'Gece hayatı', icon: '🌙' }
]

const form = reactive({
  title: '',
  destination: '',
  start_date: '',
  end_date: '',
  origin_city: '',
  origin_airport_code: '',
  budget_try: 10000,
  people_count: 1,
  nature_weight: 25,
  food_weight: 25,
  history_weight: 25,
  nightlife_weight: 25
})

const yukleniyor = ref(false)
const mesaj = ref('')
const basarili = ref(false)

const toplamAgirlik = computed(() =>
  Number(form.nature_weight) +
  Number(form.food_weight) +
  Number(form.history_weight) +
  Number(form.nightlife_weight)
)

// Ana sayfadaki arama çubuğundan gelen bilgilerle formu doldur
onMounted(() => {
  const q = route.query
  const metin = (v: unknown) => (typeof v === 'string' ? v : '')
  // Ana sayfada seçilen kalkış havalimanı
  if (/^[A-Z]{3}$/.test(metin(q.origin_airport_code))) {
    form.origin_airport_code = metin(q.origin_airport_code)
    form.origin_city = metin(q.origin_city)
  }
  if (metin(q.destination)) form.destination = metin(q.destination)
  if (metin(q.start_date)) form.start_date = metin(q.start_date)
  if (metin(q.end_date)) form.end_date = metin(q.end_date)
  if (Number(q.people_count) > 0) form.people_count = Number(q.people_count)
  if (Number(q.budget_try) > 0) form.budget_try = Number(q.budget_try)
})

async function seyahatOlustur() {
  mesaj.value = ''
  basarili.value = false

  if (toplamAgirlik.value !== 100) {
    mesaj.value = 'İlgi alanlarının toplamı 100 olmalıdır.'
    return
  }

  if (form.end_date <= form.start_date) {
    mesaj.value = 'Dönüş tarihi gidiş tarihinden sonra olmalıdır.'
    return
  }

  yukleniyor.value = true

  try {
    const response = await fetch('/api/trips', {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(form)
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))

      throw new Error(
        error.message || error.statusMessage ||
          (typeof error.detail === 'string' ? error.detail : '') ||
          `Seyahat oluşturulamadı (${response.status})`
      )
    }

    const yeniSeyahat = await response.json()
    basarili.value = true
    mesaj.value = 'Seyahatin başarıyla oluşturuldu!'
    emit('olusturuldu', yeniSeyahat.id)
  } catch (error) {
    mesaj.value = error instanceof Error
      ? error.message
      : 'Bir hata oluştu.'
  } finally {
    yukleniyor.value = false
  }
}
</script>

<template>
  <section class="travel-page">

    <!-- Geniş üst alan -->
    <div class="travel-banner">
      <div class="banner-copy">
        <span class="banner-label">VOYAGEAI / YENİ SEYAHAT</span>

        <h1>
          Sıradaki durağın
          <em>neresi?</em>
        </h1>

        <p>
          Yeni yerler keşfetmek için küçük bir plan yeter.
          Seyahatinin detaylarını belirle, sana özel rotanı oluşturalım.
        </p>
      </div>

      <div class="banner-art" aria-hidden="true">
        <div class="art-sun"></div>
        <div class="art-hill art-hill-back"></div>
        <div class="art-hill art-hill-front"></div>
        <div class="art-plane">✈</div>
        <div class="art-path"></div>
      </div>
    </div>

    <form class="travel-content" @submit.prevent="seyahatOlustur">

      <!-- Sol: Seyahat bilgileri -->
      <div class="travel-main">

        <div class="section-heading">
          <div>
            <span class="section-kicker">SEYAHAT DETAYLARI</span>
            <h2>Yolculuğunu planla</h2>
          </div>
          <p>Nereye, ne zaman, kimlerle?</p>
        </div>

        <div class="destination-strip">
          <div class="field">
            <span class="strip-baslik">Nereye gidiyorsun?</span>
            <SehirSecici v-model="form.destination" id-on-eki="yeni-seyahat" />
            <span class="strip-not">
              Karar vermediysen boş bırak; sana uygun şehirleri biz önerelim.
            </span>
          </div>

          <div class="destination-mark" aria-hidden="true">
            ↗
          </div>
        </div>

        <div class="field full-field">
          <label for="trip-title">Seyahatine bir isim ver</label>
          <input
            id="trip-title"
            v-model="form.title"
            required
            maxlength="150"
            placeholder="Örn. Arkadaşlarla yaz tatili"
          />
        </div>

        <div class="field-grid">
          <div class="field">
            <label for="trip-start">Gidiş tarihi</label>
            <input
              id="trip-start"
              v-model="form.start_date"
              type="date"
              required
            />
          </div>

          <div class="field">
            <label for="trip-end">Dönüş tarihi</label>
            <input
              id="trip-end"
              v-model="form.end_date"
              type="date"
              :min="form.start_date || undefined"
              required
            />
          </div>

          <div class="field">
            <label for="trip-origin">Kalkış şehri</label>
            <HavalimaniSecici
              id="trip-origin"
              v-model="form.origin_airport_code"
              v-model:sehir="form.origin_city"
              required
            />
          </div>

          <div class="field">
            <label for="trip-airport">Havalimanı kodu</label>
            <input
              id="trip-airport"
              v-model="form.origin_airport_code"
              readonly
              required
              placeholder="Otomatik belirlenecek"
              class="readonly-field"
            />
          </div>
        </div>

        <div class="soft-divider"></div>

        <div class="section-heading compact">
          <div>
            <span class="section-kicker">BÜTÇE & YOLCULAR</span>
            <h2>Biraz da detaylar</h2>
          </div>
        </div>

        <div class="field-grid">
          <div class="field">
            <label for="trip-budget">Toplam bütçe (TL)</label>
            <input
              id="trip-budget"
              v-model.number="form.budget_try"
              type="number"
              min="0.01"
              step="any"
              required
            />
          </div>

          <div class="field">
            <label for="trip-people">Kaç kişisiniz?</label>
            <input
              id="trip-people"
              v-model.number="form.people_count"
              type="number"
              min="1"
              step="1"
              required
            />
          </div>
        </div>

        <div class="travel-tip">
          <span class="tip-icon">✦</span>
          <p>
            Seyahat bilgilerini belirledikten sonra uçuş ve
            konaklama seçeneklerini inceleyebilirsin.
          </p>
        </div>

      </div>

      <!-- Sağ: İlgi alanları -->
      <aside class="travel-sidebar">
        <div class="sidebar-top">
          <span class="section-kicker">SANA ÖZEL</span>
          <h2>Nasıl bir gezginsin?</h2>
          <p>
            Nelerden hoşlandığını seç. Gezi önerilerini
            buna göre şekillendireceğiz.
          </p>
        </div>

        <div class="interest-list">
          <div
            v-for="alan in ilgiAlanlari"
            :key="alan.key"
            class="interest-item"
          >
            <div class="interest-heading">
              <div class="interest-name">
                <span class="interest-icon">{{ alan.icon }}</span>
                <label :for="`weight-${alan.key}`">
                  {{ alan.label }}
                </label>
              </div>

              <span class="interest-value">
                {{ form[alan.key] }}%
              </span>
            </div>

            <input
              :id="`weight-${alan.key}`"
              v-model.number="form[alan.key]"
              type="range"
              min="0"
              max="100"
              step="1"
              class="interest-range"
              :aria-label="alan.label"
            />
          </div>
        </div>

        <div class="interest-total">
          <span>Toplam dağılım</span>
          <strong :class="toplamAgirlik === 100 ? 'total-good' : 'total-bad'">
            {{ toplamAgirlik }} / 100
          </strong>
        </div>

        <div class="total-track">
          <div
            class="total-fill"
            :style="{
              width: `${Math.min(100, Math.max(0, toplamAgirlik))}%`
            }"
          ></div>
        </div>

        <p v-if="toplamAgirlik !== 100" class="total-note">
          Toplamın 100 olması gerekiyor.
        </p>

        <p v-else class="total-ready">
          ✓ Tercihlerin hazır
        </p>

        <button
          type="submit"
          class="submit-button"
          :disabled="yukleniyor || toplamAgirlik !== 100"
        >
          <span>
            {{ yukleniyor ? 'Oluşturuluyor...' : 'Seyahatimi oluştur' }}
          </span>
          <span aria-hidden="true">↗</span>
        </button>

        <p
          v-if="mesaj"
          role="status"
          class="submit-message"
          :class="basarili ? 'message-success' : 'message-error'"
        >
          {{ mesaj }}
        </p>
      </aside>
    </form>
  </section>
</template>

<style scoped>
.travel-page {
  --ink: #293042;
  --muted: #737d90;
  --blue: #789bd6;
  --lilac: #b6a4da;
  --pink: #e8b8ca;

  width: 100%;
  max-width: none;
  min-width: 0;
  margin: 0;
  padding: 0 0 40px;
  color: var(--ink);
  font-family:
    "Nunito Sans",
    "Segoe UI",
    system-ui,
    sans-serif;
}

.travel-banner {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 285px;
  padding: 48px clamp(24px, 5vw, 80px);
  overflow: hidden;
  border-radius: 24px;
  background: linear-gradient(
    110deg,
    #e1eafb 0%,
    #eee5f7 54%,
    #f9dfe9 100%
  );
}

.banner-copy {
  position: relative;
  z-index: 2;
  max-width: 690px;
}

.banner-label {
  color: #677fae;
  font-size: 11px;
  font-weight: 750;
  letter-spacing: 2px;
}

.banner-copy h1 {
  margin: 18px 0 16px;
  font-size: clamp(32px, 4vw, 53px);
  line-height: 1.12;
  font-weight: 750;
  letter-spacing: -1.7px;
}

.banner-copy h1 em {
  color: #8572b7;
  font-family: Georgia, serif;
  font-weight: 400;
}

.banner-copy p {
  max-width: 550px;
  color: #63708a;
  font-size: 15px;
  line-height: 1.75;
}

.banner-art {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 37%;
  height: 100%;
  overflow: hidden;
  pointer-events: none;
}

.art-sun {
  position: absolute;
  top: 36px;
  right: 25%;
  width: 135px;
  height: 135px;
  border-radius: 50%;
  background: #f9cfdb;
  opacity: 0.9;
}

.art-hill {
  position: absolute;
  width: 120%;
  height: 180px;
  border-radius: 50% 50% 0 0;
}

.art-hill-back {
  right: -20%;
  bottom: -95px;
  transform: rotate(-12deg);
  background: #c3b7e7;
}

.art-hill-front {
  right: -35%;
  bottom: -115px;
  transform: rotate(12deg);
  background: #a8bee8;
}

.art-plane {
  position: absolute;
  top: 60px;
  right: 35%;
  color: #7c86bb;
  font-size: 58px;
  transform: rotate(-18deg);
}

.art-path {
  position: absolute;
  top: 140px;
  right: 43%;
  width: 110px;
  height: 65px;
  border-bottom: 2px dashed #a9a1d4;
  border-radius: 50%;
  transform: rotate(20deg);
}

.travel-content {
  display: grid;
  grid-template-columns: minmax(0, 1.65fr) minmax(310px, 0.9fr);
  gap: clamp(24px, 3vw, 52px);
  width: 100%;
  padding: 38px clamp(20px, 4vw, 64px);
}

.travel-main {
  min-width: 0;
}

.section-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 15px;
  margin-bottom: 25px;
}

.section-kicker {
  display: block;
  margin-bottom: 9px;
  color: #8b83ba;
  font-size: 11px;
  font-weight: 750;
  letter-spacing: 1.6px;
}

.section-heading h2,
.sidebar-top h2 {
  margin: 0;
  font-size: clamp(21px, 2vw, 27px);
  font-weight: 700;
  letter-spacing: -0.65px;
}

.section-heading > p {
  color: var(--muted);
  font-size: 13px;
}

.destination-strip {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 18px;
  margin-bottom: 22px;
  border: 1px solid #e4def3;
  border-radius: 17px;
  background: #f6f2fc;
}

.destination-strip .field {
  flex: 1;
  gap: 10px;
}

.strip-baslik {
  color: #4c5870;
  font-size: 13px;
  font-weight: 800;
}

.strip-not {
  color: #737d90;
  font-size: 12px;
}

.destination-strip input {
  border: none;
  background: transparent;
  padding-left: 0;
  font-size: 17px;
  font-weight: 600;
}

.destination-strip input:focus {
  box-shadow: none;
}

.destination-mark {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 43px;
  height: 43px;
  border-radius: 50%;
  flex: none;
  background: #e7defa;
  color: #8572b7;
  font-size: 23px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 9px;
  min-width: 0;
}

.field label {
  color: #4c5870;
  font-size: 13px;
  font-weight: 650;
}

.field input,
.field select {
  width: 100%;
  height: 53px;
  padding: 0 16px;
  border: 1px solid #dfe3ec;
  border-radius: 12px;
  outline: none;
  background: #fff;
  color: var(--ink);
  font: inherit;
  font-size: 14px;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.field input::placeholder {
  color: #a0a9b8;
}

.field input:focus,
.field select:focus {
  border-color: #9a9bd8;
  box-shadow: 0 0 0 3px #eae8f8;
}

.field .readonly-field {
  background: #f2f4f8;
  color: #78839a;
}

.full-field {
  margin-bottom: 22px;
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 22px;
}

.soft-divider {
  height: 1px;
  margin: 36px 0 32px;
  background: linear-gradient(
    90deg,
    #d6e2f6,
    #e8dced,
    transparent
  );
}

.section-heading.compact {
  margin-bottom: 24px;
}

.travel-tip {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 30px;
  padding: 18px 20px;
  border-radius: 14px;
  background: #f8f2f7;
}

.tip-icon {
  color: #ba8ca9;
  font-size: 24px;
}

.travel-tip p {
  color: #77718b;
  font-size: 13px;
  line-height: 1.6;
}

.travel-sidebar {
  align-self: start;
  padding: 30px;
  border: 1px solid #e7e0f0;
  border-radius: 22px;
  background: linear-gradient(
    160deg,
    #faf7ff,
    #fff8fb 70%,
    #f5f7ff
  );
  box-shadow: 0 12px 35px rgba(105, 91, 153, 0.07);
}

.sidebar-top {
  margin-bottom: 28px;
}

.sidebar-top p {
  margin-top: 12px;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.7;
}

.interest-list {
  display: grid;
  gap: 24px;
}

.interest-heading,
.interest-name {
  display: flex;
  align-items: center;
}

.interest-heading {
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.interest-name {
  gap: 11px;
}

.interest-name label {
  font-size: 14px;
  font-weight: 650;
}

.interest-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 11px;
  background: #eee8f7;
  font-size: 18px;
}

.interest-value {
  color: #8170b2;
  font-size: 14px;
  font-weight: 750;
}

.interest-range {
  width: 100%;
  accent-color: #a79ad5;
  cursor: pointer;
}

.interest-total {
  display: flex;
  justify-content: space-between;
  margin-top: 32px;
  padding-top: 20px;
  border-top: 1px solid #e5deee;
  font-size: 14px;
}

.total-good {
  color: #3c8b72;
}

.total-bad {
  color: #ba6889;
}

.total-track {
  height: 7px;
  margin-top: 13px;
  overflow: hidden;
  border-radius: 20px;
  background: #e8e3f1;
}

.total-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(
    90deg,
    #84a5dc,
    #b4a1dc,
    #e8b8ca
  );
  transition: width 0.2s;
}

.total-note,
.total-ready {
  margin-top: 10px;
  font-size: 12px;
}

.total-note {
  color: #b45f7b;
}

.total-ready {
  color: #3c8b72;
}

.submit-button {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  width: 100%;
  min-height: 55px;
  margin-top: 30px;
  padding: 0 21px;
  border: none;
  border-radius: 13px;
  background: linear-gradient(
    105deg,
    #7798d2,
    #a18bcd
  );
  color: white;
  font: inherit;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.submit-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 10px 24px rgba(123, 133, 202, 0.22);
}

.submit-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.submit-button span:last-child {
  font-size: 22px;
  font-weight: 400;
}

.submit-message {
  margin-top: 15px;
  font-size: 13px;
  line-height: 1.5;
}

.message-success {
  color: #3c8b72;
}

.message-error {
  color: #b45f7b;
}

@media (max-width: 1000px) {
  .travel-content {
    grid-template-columns: 1fr;
  }

  .travel-sidebar {
    width: 100%;
  }
}

@media (max-width: 640px) {
  .travel-banner {
    min-height: 230px;
    padding: 32px 24px;
  }

  .banner-art {
    opacity: 0.3;
    width: 65%;
  }

  .banner-copy h1 {
    font-size: 34px;
  }

  .travel-content {
    padding: 28px 12px;
  }

  .field-grid {
    grid-template-columns: 1fr;
    gap: 20px;
  }

  .section-heading {
    align-items: start;
    flex-direction: column;
  }

  .travel-sidebar {
    padding: 24px;
  }
}
</style>
