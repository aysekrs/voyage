
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import SeyahatDetay from './SeyahatDetay.vue'
import SeyahatDuzenle from './SeyahatDuzenle.vue'

interface Seyahat {
  id: number
  title: string
  destination: string
  start_date: string
  end_date: string
  created_at: string
  role: string
}

const seyahatler = ref<Seyahat[]>([])
const yukleniyor = ref(false)
const hata = ref('')
const secilenSeyahatId = ref<number | null>(null)
const duzenlenenSeyahatId = ref<number | null>(null)
const siliniyorId = ref<number | null>(null)

async function seyahatleriGetir() {
  yukleniyor.value = true
  hata.value = ''

  try {
    const response = await fetch('/api/trips', {
      credentials: 'include'
    })

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error(
          'Seyahatlerini görmek için giriş yapmalısın.'
        )
      }

      throw new Error('Seyahatler yüklenemedi.')
    }

    const data: { trips: Seyahat[] } = await response.json()
    seyahatler.value = data.trips
  } catch (error) {
    hata.value = error instanceof Error
      ? error.message
      : 'Bir hata oluştu.'
  } finally {
    yukleniyor.value = false
  }
}

function tarihFormatla(tarih: string) {
  if (!tarih) return '-'

  const [yil, ay, gun] = tarih.slice(0, 10).split('-')
  return `${gun}.${ay}.${yil}`
}

function gunSayisi(baslangic: string, bitis: string) {
  const baslangicMs = Date.parse(`${baslangic.slice(0, 10)}T00:00:00Z`)
  const bitisMs = Date.parse(`${bitis.slice(0, 10)}T00:00:00Z`)

  if (!Number.isFinite(baslangicMs) || !Number.isFinite(bitisMs)) {
    return null
  }

  const fark = Math.round(
    (bitisMs - baslangicMs) / (1000 * 60 * 60 * 24)
  )

  return fark >= 0 ? fark : null
}

async function seyahatSil(seyahat: Seyahat) {
  if (seyahat.role !== 'owner') return

  const onay = window.confirm(
    `"${seyahat.title}" seyahatini silmek istediğine emin misin?`
  )

  if (!onay) return

  siliniyorId.value = seyahat.id
  hata.value = ''

  try {
    const response = await fetch(
      `/api/trips/${seyahat.id}`,
      {
        method: 'DELETE',
        credentials: 'include'
      }
    )

    if (!response.ok) {
      throw new Error(
        response.status === 401
          ? 'Oturum açman gerekiyor.'
          : `Seyahat silinemedi (${response.status}).`
      )
    }

    if (secilenSeyahatId.value === seyahat.id) {
      secilenSeyahatId.value = null
    }

    if (duzenlenenSeyahatId.value === seyahat.id) {
      duzenlenenSeyahatId.value = null
    }

    seyahatler.value = seyahatler.value.filter(
      item => item.id !== seyahat.id
    )
  } catch (error) {
    hata.value = error instanceof Error
      ? error.message
      : 'Silme sırasında hata oluştu.'
  } finally {
    siliniyorId.value = null
  }
}

onMounted(seyahatleriGetir)
</script>

<template>
  <section class="trips-page">
    <!-- Üst başlık -->
    <div class="trips-banner">
      <div class="banner-content">
        <span class="banner-eyebrow">
          VOYAGEAI / SEYAHATLERİM
        </span>

        <h1>
          Biriktirdiğin
          <em>yolculuklar.</em>
        </h1>

        <p>
          Planladığın tüm seyahatler burada.
          Dilediğin zaman detaylarına göz atabilir,
          planlarını güncelleyebilirsin.
        </p>
      </div>

      <div class="banner-decoration" aria-hidden="true">
        <div class="decoration-circle"></div>
        <div class="decoration-circle-small"></div>
        <div class="decoration-arc"></div>
        <span class="decoration-plane">✈</span>
      </div>
    </div>

    <!-- Liste başlığı -->
    <div class="trips-toolbar">
      <div>
        <span class="toolbar-eyebrow">KEŞİF DEFTERİN</span>
        <h2>Seyahat planların</h2>

        <p v-if="!yukleniyor && !hata">
          {{ seyahatler.length }} seyahat
        </p>
      </div>

      <button
        type="button"
        class="refresh-button"
        :disabled="yukleniyor"
        @click="seyahatleriGetir"
      >
        <span aria-hidden="true">↻</span>
        {{ yukleniyor ? 'Yükleniyor...' : 'Listeyi yenile' }}
      </button>
    </div>

    <!-- Durum mesajları -->
    <div v-if="yukleniyor" class="state-box">
      Seyahatlerin yükleniyor...
    </div>

    <div v-if="hata" class="state-box error-box" role="alert">
      <p>{{ hata }}</p>
      <button type="button" @click="seyahatleriGetir">
        Tekrar dene
      </button>
    </div>

    <div
      v-if="!yukleniyor && !hata && seyahatler.length === 0"
      class="empty-state"
    >
      <span class="empty-icon">✈</span>
      <h3>Henüz bir seyahatin yok.</h3>
      <p>
        İlk seyahatini oluşturduğunda burada görebileceksin.
      </p>
    </div>

    <!-- Seyahat kartları -->
    <div
      v-if="!yukleniyor && seyahatler.length"
      class="trips-list"
    >
      <article
        v-for="(seyahat, index) in seyahatler"
        :key="seyahat.id"
        class="trip-card"
      >
        <div
          class="trip-card-accent"
          :class="index % 3 === 0
            ? 'accent-blue'
            : index % 3 === 1
              ? 'accent-lilac'
              : 'accent-pink'"
        >
          <span class="accent-plane" aria-hidden="true">✈</span>
          <span class="accent-text">VOYAGEAI</span>
        </div>

        <div class="trip-card-content">
          <div class="trip-card-top">
            <div>
              <span class="trip-location">
                <span aria-hidden="true">⌖</span>
                {{ seyahat.destination }}
              </span>

              <h3>{{ seyahat.title }}</h3>
            </div>

            <span
              class="trip-role"
              :class="seyahat.role === 'owner'
                ? 'role-owner'
                : 'role-member'"
            >
              {{ seyahat.role === 'owner' ? 'Sahibi' : 'Üye' }}
            </span>
          </div>

          <div class="trip-meta">
            <span>
              <span class="meta-icon" aria-hidden="true">◷</span>
              {{ tarihFormatla(seyahat.start_date) }}
              –
              {{ tarihFormatla(seyahat.end_date) }}
            </span>

            <span v-if="gunSayisi(seyahat.start_date, seyahat.end_date) !== null">
              <span class="meta-icon" aria-hidden="true">☼</span>
              {{ gunSayisi(seyahat.start_date, seyahat.end_date) }} gece
            </span>
          </div>

          <div class="trip-actions">
            <button
              type="button"
              class="details-button"
              @click="
                secilenSeyahatId =
                  secilenSeyahatId === seyahat.id
                    ? null
                    : seyahat.id
              "
            >
              {{
                secilenSeyahatId === seyahat.id
                  ? 'Detayları kapat'
                  : 'Detayları gör'
              }}
              <span aria-hidden="true">↗</span>
            </button>

            <template v-if="seyahat.role === 'owner'">
              <button
                type="button"
                class="edit-button"
                @click="duzenlenenSeyahatId = seyahat.id"
              >
                Düzenle
              </button>

              <button
                type="button"
                class="delete-button"
                :disabled="siliniyorId === seyahat.id"
                @click="seyahatSil(seyahat)"
              >
                {{ siliniyorId === seyahat.id ? 'Siliniyor...' : 'Sil' }}
              </button>
            </template>
          </div>
        </div>

        <!-- Seçilen seyahatin detayları -->
        <div
          v-if="secilenSeyahatId === seyahat.id"
          class="trip-expanded"
        >
          <SeyahatDetay
            :trip-id="seyahat.id"
            @kapat="secilenSeyahatId = null"
          />
        </div>

        <!-- Düzenleme formu -->
        <div
          v-if="duzenlenenSeyahatId === seyahat.id"
          class="trip-expanded"
        >
          <SeyahatDuzenle
            :trip-id="seyahat.id"
            @kapat="duzenlenenSeyahatId = null"
            @guncellendi="
              duzenlenenSeyahatId = null;
              secilenSeyahatId = null;
              seyahatleriGetir()
            "
          />
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.trips-page {
  --ink: #293042;
  --muted: #758097;
  --blue: #789bd6;
  --lilac: #b6a4da;
  --pink: #e8b8ca;

  width: 100%;
  max-width: none;
  min-width: 0;
  padding-bottom: 45px;
  color: var(--ink);
  font-family:
    "Nunito Sans",
    "Segoe UI",
    system-ui,
    sans-serif;
}

/* Üst banner */
.trips-banner {
  position: relative;
  display: flex;
  align-items: center;
  min-height: 275px;
  padding: 45px clamp(25px, 5vw, 80px);
  overflow: hidden;
  border-radius: 24px;
  background: linear-gradient(
    115deg,
    #e5ecfb 0%,
    #f0e8f8 53%,
    #f8e1eb 100%
  );
}

.banner-content {
  position: relative;
  z-index: 2;
  max-width: 700px;
}

.banner-eyebrow {
  color: #7288b6;
  font-size: 11px;
  font-weight: 750;
  letter-spacing: 1.8px;
}

.banner-content h1 {
  margin: 18px 0 14px;
  font-size: clamp(32px, 4vw, 52px);
  font-weight: 750;
  line-height: 1.15;
  letter-spacing: -1.6px;
}

.banner-content h1 em {
  color: #8e78bd;
  font-family: Georgia, serif;
  font-weight: 400;
}

.banner-content p {
  max-width: 560px;
  color: #65718a;
  font-size: 15px;
  line-height: 1.75;
}

.banner-decoration {
  position: absolute;
  right: 4%;
  top: 0;
  width: 35%;
  height: 100%;
  pointer-events: none;
}

.decoration-circle {
  position: absolute;
  right: 15%;
  top: 36px;
  width: 170px;
  height: 170px;
  border-radius: 50%;
  background: #eac1d7;
  opacity: 0.6;
}

.decoration-circle-small {
  position: absolute;
  right: 0;
  bottom: -65px;
  width: 230px;
  height: 230px;
  border-radius: 50%;
  background: #bdcbed;
  opacity: 0.7;
}

.decoration-arc {
  position: absolute;
  right: 25%;
  bottom: 40px;
  width: 190px;
  height: 95px;
  border-bottom: 2px dashed #b0a0d1;
  border-radius: 50%;
  transform: rotate(-25deg);
}

.decoration-plane {
  position: absolute;
  right: 32%;
  top: 78px;
  color: #788dc4;
  font-size: 65px;
  transform: rotate(-18deg);
}

/* Başlık */
.trips-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  padding: 38px clamp(20px, 4vw, 64px) 25px;
}

.toolbar-eyebrow {
  color: #9184c1;
  font-size: 11px;
  font-weight: 750;
  letter-spacing: 1.5px;
}

.trips-toolbar h2 {
  margin-top: 8px;
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.6px;
}

.trips-toolbar p {
  margin-top: 6px;
  color: var(--muted);
  font-size: 13px;
}

.refresh-button {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 11px 17px;
  border: 1px solid #d9ddeb;
  border-radius: 12px;
  background: white;
  color: #526487;
  font-size: 13px;
  font-weight: 650;
  cursor: pointer;
}

.refresh-button:hover {
  background: #f1f4fc;
}

.refresh-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.refresh-button span {
  font-size: 20px;
}

/* Kartlar */
.trips-list {
  display: grid;
  gap: 20px;
  padding: 0 clamp(20px, 4vw, 64px);
}

.trip-card {
  display: grid;
  grid-template-columns: 190px minmax(0, 1fr);
  overflow: hidden;
  border: 1px solid #e5e7f0;
  border-radius: 20px;
  background: white;
  box-shadow: 0 8px 25px rgba(63, 75, 114, 0.045);
  transition: box-shadow 0.2s, transform 0.2s;
}

.trip-card:hover {
  box-shadow: 0 12px 32px rgba(63, 75, 114, 0.085);
  transform: translateY(-2px);
}

.trip-card-accent {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 190px;
  overflow: hidden;
}

.accent-blue {
  background: linear-gradient(145deg, #dce9fc, #b4c8ed);
}

.accent-lilac {
  background: linear-gradient(145deg, #ede4fa, #c9b9e9);
}

.accent-pink {
  background: linear-gradient(145deg, #f9e4ec, #e9bed2);
}

.trip-card-accent::before {
  content: "";
  position: absolute;
  width: 160px;
  height: 160px;
  border: 1px solid rgba(255, 255, 255, 0.65);
  border-radius: 50%;
  transform: translate(35px, 45px);
}

.trip-card-accent::after {
  content: "";
  position: absolute;
  width: 105px;
  height: 105px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.25);
  transform: translate(-55px, -65px);
}

.accent-plane {
  position: relative;
  z-index: 1;
  color: rgba(82, 105, 162, 0.8);
  font-size: 62px;
  transform: rotate(-20deg);
}

.accent-text {
  position: absolute;
  bottom: 20px;
  left: 20px;
  color: rgba(72, 85, 126, 0.7);
  font-size: 10px;
  font-weight: 750;
  letter-spacing: 2px;
}

.trip-card-content {
  min-width: 0;
  padding: 25px 30px;
}

.trip-card-top {
  display: flex;
  justify-content: space-between;
  align-items: start;
  gap: 20px;
}

.trip-location {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #8c7bb8;
  font-size: 12px;
  font-weight: 700;
}

.trip-location span {
  font-size: 19px;
}

.trip-card h3 {
  margin-top: 7px;
  font-size: clamp(19px, 2vw, 24px);
  font-weight: 700;
  letter-spacing: -0.5px;
  overflow-wrap: anywhere;
}

.trip-role {
  flex-shrink: 0;
  padding: 7px 12px;
  border-radius: 30px;
  font-size: 11px;
  font-weight: 700;
}

.role-owner {
  background: #e8effb;
  color: #6482b5;
}

.role-member {
  background: #f2ebfa;
  color: #9279b7;
}

.trip-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 25px;
  margin-top: 18px;
  color: var(--muted);
  font-size: 13px;
}

.trip-meta > span {
  display: flex;
  align-items: center;
  gap: 7px;
}

.meta-icon {
  color: #9d91c5;
  font-size: 18px;
}

.trip-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 24px;
}

.trip-actions button {
  min-height: 40px;
  padding: 9px 15px;
  border-radius: 10px;
  font: inherit;
  font-size: 13px;
  font-weight: 650;
  cursor: pointer;
}

.details-button {
  display: flex;
  align-items: center;
  gap: 15px;
  border: none;
  background: linear-gradient(105deg, #789bd6, #a18ccd);
  color: white;
}

.details-button span {
  font-size: 17px;
}

.edit-button {
  border: 1px solid #dcd6ec;
  background: #f7f3fd;
  color: #7c6aaa;
}

.delete-button {
  margin-left: auto;
  border: 1px solid #f0dce5;
  background: #fff7f9;
  color: #b66f87;
}

.delete-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.trip-expanded {
  grid-column: 1 / -1;
  padding: 10px 25px 25px;
  border-top: 1px solid #e9eaf1;
  background: #fbfcff;
}

/* Durumlar */
.state-box,
.empty-state {
  margin: 0 clamp(20px, 4vw, 64px);
  padding: 30px;
  border: 1px solid #e5e7f0;
  border-radius: 18px;
  background: white;
  color: var(--muted);
}

.error-box {
  color: #b45f7b;
}

.error-box button {
  margin-top: 12px;
  color: #7668ad;
  font-weight: 700;
  text-decoration: underline;
}

.empty-state {
  padding: 65px 25px;
  text-align: center;
}

.empty-icon {
  display: block;
  margin-bottom: 18px;
  color: #a29bd0;
  font-size: 52px;
}

.empty-state h3 {
  color: var(--ink);
  font-size: 21px;
  font-weight: 700;
}

.empty-state p {
  margin-top: 10px;
  font-size: 14px;
}

@media (max-width: 850px) {
  .trip-card {
    grid-template-columns: 135px minmax(0, 1fr);
  }

  .trip-card-accent {
    min-height: 180px;
  }

  .trip-card-content {
    padding: 22px;
  }
}

@media (max-width: 640px) {
  .trips-banner {
    min-height: 230px;
    padding: 32px 24px;
  }

  .banner-decoration {
    opacity: 0.3;
    width: 65%;
  }

  .trips-toolbar {
    align-items: flex-start;
    padding: 30px 12px 22px;
  }

  .trips-toolbar h2 {
    font-size: 23px;
  }

  .trips-list {
    padding: 0 12px;
  }

  .trip-card {
    grid-template-columns: 1fr;
  }

  .trip-card-accent {
    min-height: 110px;
  }

  .accent-plane {
    font-size: 43px;
  }

  .trip-card-content {
    padding: 20px;
  }

  .trip-card-top {
    gap: 10px;
  }

  .trip-actions {
    gap: 8px;
  }

  .delete-button {
    margin-left: 0;
  }

  .trip-expanded {
    padding: 10px 12px 20px;
  }
}
</style>
