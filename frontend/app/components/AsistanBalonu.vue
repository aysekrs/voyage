<script setup lang="ts">
// Sağ alttaki AI asistan balonu (5. hafta, Kişi B). Her sayfada görünür;
// tıklayınca AiSohbet kompakt panelde açılır. Sohbet backend'de tutulduğu için
// /asistan sayfasıyla aynı konuşmayı gösterir.
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const route = useRoute()
const { kullanici, kontrolEdildi, yenile } = useKullanici()

const acik = useState('asistan-acik', () => false)
// Panel bir kez açılınca bileşen yerinde kalır (yazılan metin kaybolmasın)
const birKezAcildi = ref(false)
const ipucu = ref(false)

const gizli = computed(() => route.path === '/asistan' || route.path.startsWith('/login'))

watch(acik, (deger) => {
  if (deger) {
    birKezAcildi.value = true
    ipucu.value = false
  }
})

// Sayfa değişince panel açık kalır ama /asistan'a gidilirse kapanır
watch(gizli, (deger) => {
  if (deger) acik.value = false
})

function kapatEsc(e: KeyboardEvent) {
  if (e.key === 'Escape') acik.value = false
}

function ipucuKapat() {
  ipucu.value = false
  try {
    localStorage.setItem('voyage-asistan-ipucu', '1')
  } catch {
    // tarayıcı depolaması kapalıysa önemli değil
  }
}

onMounted(() => {
  if (!kontrolEdildi.value) yenile()
  window.addEventListener('keydown', kapatEsc)
  // İlk ziyarette küçük bir "merhaba" baloncuğu
  try {
    if (!localStorage.getItem('voyage-asistan-ipucu')) {
      setTimeout(() => { if (!acik.value) ipucu.value = true }, 1500)
    }
  } catch {
    // yok say
  }
})

onBeforeUnmount(() => window.removeEventListener('keydown', kapatEsc))

async function seyahatOlustu(id: number) {
  acik.value = false
  await navigateTo(`/seyahatler/${id}`)
}
</script>

<template>
  <div v-if="!gizli" class="asistan-balonu">
    <!-- Maskot çizimi bir kez tanımlanır; sticker ve panel başlığı kullanır -->
    <svg class="tanimlar" width="0" height="0" aria-hidden="true" focusable="false">
        <defs>
          <linearGradient id="maskot-gok" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="#789bd6" />
            <stop offset="1" stop-color="#b6a4da" />
          </linearGradient>
          <!-- Bulut maskot: başlıkta da tekrar kullanılır -->
          <g id="voyage-maskot">
            <circle cx="32" cy="32" r="32" fill="url(#maskot-gok)" />
            <path
              d="M18 41c-4.4 0-8-3.4-8-7.6 0-3.9 3-7.1 6.9-7.5C18.3 20.8 22.9 17 28.4 17c4.6 0 8.6 2.7 10.4 6.6 1-.4 2-.6 3.1-.6 4.6 0 8.4 3.6 8.6 8.2 3.1.6 5.5 3.3 5.5 6.5 0 3.7-3 6.6-6.7 6.6H18z"
              fill="#ffffff"
            />
            <circle cx="27" cy="32" r="2.4" fill="#293042" />
            <circle cx="39" cy="32" r="2.4" fill="#293042" />
            <circle cx="27.8" cy="31.2" r="0.8" fill="#ffffff" />
            <circle cx="39.8" cy="31.2" r="0.8" fill="#ffffff" />
            <ellipse cx="22.5" cy="37" rx="2.6" ry="1.6" fill="#e8b8ca" />
            <ellipse cx="43.5" cy="37" rx="2.6" ry="1.6" fill="#e8b8ca" />
            <path d="M29.5 37.5q3.5 3 7 0" stroke="#293042" stroke-width="1.8" fill="none" stroke-linecap="round" />
            <!-- küçük kâğıt uçak -->
            <path d="M44 12l10-3.5-4.5 9.5-1.8-3.6z" fill="#ffffff" />
            <path d="M47.7 14.4l1.8 3.6 1-2.2" fill="#dcd3f0" />
          </g>
        </defs>
    </svg>

    <!-- Panel -->
    <Transition name="panel">
      <section v-show="acik" class="panel" role="dialog" aria-label="VoyageAI asistan">
        <header class="panel-ust">
          <span class="mini-maskot" aria-hidden="true">
            <svg viewBox="0 0 64 64"><use href="#voyage-maskot" /></svg>
          </span>
          <div class="panel-baslik">
            <strong>Voyage asistan</strong>
            <span>Seyahatini anlat, birlikte planlayalım</span>
          </div>
          <NuxtLink to="/asistan" class="ikon-buton" title="Tam ekran aç" aria-label="Tam ekran aç">⤢</NuxtLink>
          <button type="button" class="ikon-buton" aria-label="Kapat" @click="acik = false">✕</button>
        </header>

        <div class="panel-govde">
          <div v-if="!kontrolEdildi" class="bilgi">Yükleniyor...</div>
          <div v-else-if="!kullanici" class="bilgi">
            <p>Asistanla seyahat planlamak için önce giriş yapmalısın.</p>
            <NuxtLink :to="{ path: '/login', query: { redirect: route.fullPath } }" class="v-buton" @click="acik = false">
              Giriş yap
            </NuxtLink>
          </div>
          <AiSohbet v-else-if="birKezAcildi" kompakt @olusturuldu="seyahatOlustu" />
        </div>
      </section>
    </Transition>

    <!-- İlk ziyaret ipucu -->
    <Transition name="ipucu">
      <div v-if="ipucu && !acik" class="ipucu" role="status">
        <button type="button" class="ipucu-kapat" aria-label="İpucunu kapat" @click="ipucuKapat">✕</button>
        Merhaba! 👋 Seyahatini bir cümleyle anlat, gerisini birlikte planlayalım.
      </div>
    </Transition>

    <!-- Sticker / açma düğmesi -->
    <button
      type="button"
      :class="['sticker', { acik }]"
      :aria-label="acik ? 'Asistanı kapat' : 'AI asistanı aç'"
      :aria-expanded="acik"
      @click="acik = !acik"
    >
      <svg class="maskot" viewBox="0 0 64 64" aria-hidden="true">
        <use href="#voyage-maskot" />
      </svg>
      <span class="kapat-isareti" aria-hidden="true">✕</span>
    </button>
  </div>
</template>

<style scoped>
.asistan-balonu {
  position: fixed;
  right: clamp(14px, 3vw, 28px);
  bottom: clamp(14px, 3vw, 28px);
  z-index: 60;
  font-family: var(--v-font);
}

.tanimlar {
  position: absolute;
  width: 0;
  height: 0;
  overflow: hidden;
}

/* ---------- sticker ---------- */
.sticker {
  position: relative;
  display: grid;
  place-items: center;
  width: 68px;
  height: 68px;
  margin-left: auto;
  padding: 0;
  border: 4px solid white;
  border-radius: 50%;
  background: white;
  box-shadow: 0 14px 34px rgba(133, 114, 183, 0.38);
  cursor: pointer;
  transform: rotate(-6deg);
  transition: transform 0.25s, box-shadow 0.25s;
  animation: suzul 3.2s ease-in-out infinite;
}

.sticker:hover {
  transform: rotate(0deg) scale(1.07);
  box-shadow: 0 18px 40px rgba(133, 114, 183, 0.45);
}

.maskot {
  width: 100%;
  height: 100%;
  transition: opacity 0.2s, transform 0.2s;
}

.kapat-isareti {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--v-gradient-button);
  color: white;
  font-size: 22px;
  font-weight: 800;
  opacity: 0;
  transition: opacity 0.2s;
}

.sticker.acik {
  animation: none;
  transform: rotate(0deg);
}

.sticker.acik .kapat-isareti {
  opacity: 1;
}

@keyframes suzul {
  0%, 100% { translate: 0 0; }
  50% { translate: 0 -5px; }
}

@media (prefers-reduced-motion: reduce) {
  .sticker { animation: none; }
}

/* ---------- ipucu ---------- */
.ipucu {
  position: relative;
  width: 230px;
  margin: 0 6px 12px auto;
  padding: 14px 30px 14px 16px;
  border: 1px solid #eeecf4;
  border-radius: 18px 18px 6px 18px;
  background: white;
  box-shadow: var(--v-shadow);
  color: var(--v-ink);
  font-size: 14px;
  font-weight: 600;
  line-height: 1.45;
}

.ipucu-kapat {
  position: absolute;
  top: 6px;
  right: 8px;
  border: 0;
  background: none;
  color: var(--v-soft);
  cursor: pointer;
}

/* ---------- panel ---------- */
.panel {
  position: absolute;
  right: 0;
  bottom: 84px;
  display: flex;
  flex-direction: column;
  width: min(420px, calc(100vw - 28px));
  max-height: min(680px, calc(100dvh - 120px));
  overflow: hidden;
  border: 1px solid #eeecf4;
  border-radius: 24px;
  background: white;
  box-shadow: 0 24px 60px rgba(77, 86, 140, 0.22);
  transform-origin: bottom right;
}

.panel-ust {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 14px 14px 16px;
  background: var(--v-gradient-soft);
}

.mini-maskot {
  flex: none;
  width: 38px;
  height: 38px;
}

.mini-maskot svg {
  width: 100%;
  height: 100%;
}

.panel-baslik {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
}

.panel-baslik strong {
  color: var(--v-ink);
  font-weight: 800;
}

.panel-baslik span {
  overflow: hidden;
  color: var(--v-muted);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ikon-buton {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.7);
  color: var(--v-ink);
  font-size: 15px;
  text-decoration: none;
  cursor: pointer;
}

.ikon-buton:hover {
  background: white;
}

.panel-govde {
  flex: 1;
  overflow-y: auto;
}

.bilgi {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 12px;
  padding: 24px 18px;
  color: var(--v-muted);
}

.bilgi p {
  margin: 0;
}

/* Telefon: alttan açılan tam genişlik panel */
@media (max-width: 520px) {
  .panel {
    position: fixed;
    right: 0;
    bottom: 0;
    left: 0;
    width: 100%;
    max-height: 88dvh;
    border-radius: 24px 24px 0 0;
  }

  .sticker.acik {
    display: none;
  }
}

/* ---------- geçişler ---------- */
.panel-enter-active,
.panel-leave-active,
.ipucu-enter-active,
.ipucu-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}

.panel-enter-from,
.panel-leave-to {
  opacity: 0;
  transform: translateY(12px) scale(0.96);
}

.ipucu-enter-from,
.ipucu-leave-to {
  opacity: 0;
  transform: translateY(6px);
}
</style>
