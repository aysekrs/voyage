<script setup lang="ts">
// Şehir sayfası: gezilecek yerler + B'nin harita, günlük plan ve rota bileşenleri
import { computed, onMounted, ref } from 'vue'

interface Sehir {
  id: number
  name: string
  country: string
}

interface Yer {
  id: number
  name: string
  category: string | null
  latitude: number | null
  longitude: number | null
  visit_duration: number | null
  average_price: number | null
  price_currency?: string | null
}

const API_URL = 'http://127.0.0.1:8000'
const { fotolar, getir: fotoGetir } = useSehirFotografi()
const route = useRoute()
const sehirId = Number(route.params.id)

const sehir = ref<Sehir | null>(null)
const yerler = ref<Yer[]>([])
const yukleniyor = ref(true)
const hata = ref('')
const secilenKategori = ref('hepsi')
const secilenYerId = ref<number | null>(null)
const haritadaOlanYerler = ref<number[]>([])

const filtrelenmis = computed(() =>
  secilenKategori.value === 'hepsi'
    ? yerler.value
    : yerler.value.filter(y => y.category === secilenKategori.value)
)

const toplamSure = computed(() =>
  filtrelenmis.value.reduce((t, y) => t + (y.visit_duration ?? 0), 0)
)

function kategoriBilgisi(deger: string | null) {
  return kategoriler.find(k => k.deger === deger)
}

function sureYaz(dakika: number) {
  const saat = Math.floor(dakika / 60)
  const kalan = dakika % 60
  if (!saat) return `${kalan} dk`
  return kalan ? `${saat} sa ${kalan} dk` : `${saat} saat`
}

// Ücret, yerin kendi para biriminde (ör. 18,5 € ya da 450 ₺)
function ucretYaz(yer: Yer) {
  if (yer.average_price === null || yer.average_price === undefined) return 'Ücret bilinmiyor'
  if (Number(yer.average_price) === 0) return 'Ücretsiz'
  try {
    return new Intl.NumberFormat('tr-TR', {
      style: 'currency',
      currency: yer.price_currency || 'TRY',
      minimumFractionDigits: 0,
      maximumFractionDigits: 2
    }).format(Number(yer.average_price))
  } catch {
    return `${yer.average_price} ${yer.price_currency ?? ''}`.trim()
  }
}

function haritadaGoster(id: number) {
  secilenYerId.value = id
  document.getElementById('harita')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const foto = computed(() => fotolar.value[sehirId])

onMounted(async () => {
  try {
    const [s, y] = await Promise.all([
      $fetch<Sehir>(`${API_URL}/destinations/${sehirId}`),
      $fetch<Yer[]>(`${API_URL}/destinations/${sehirId}/places`)
    ])
    sehir.value = s
    yerler.value = y
    fotoGetir(s.id, s.name, s.country)
  } catch {
    hata.value = 'Şehir bilgileri yüklenemedi.'
  } finally {
    yukleniyor.value = false
  }
})
</script>

<template>
  <div class="kap sehir-sayfa">
    <NuxtLink to="/" class="geri">← Keşfet'e dön</NuxtLink>

    <p v-if="yukleniyor" class="durum">Yükleniyor…</p>
    <p v-else-if="hata" class="durum hata">{{ hata }}</p>

    <template v-else-if="sehir">
      <!-- Başlık -->
      <header
        class="sehir-baslik"
        :class="{ fotolu: foto?.url }"
        :style="foto?.url
          ? { backgroundImage: `linear-gradient(180deg, rgba(41,48,66,0) 30%, rgba(41,48,66,.72) 100%), url(${foto.url})` }
          : { background: sehirGecisi(sehir.id) }"
      >
        <div>
          <span class="v-ust-yazi">{{ sehir.country }}</span>
          <h1>{{ sehir.name }}</h1>
          <div class="ozet">
            <span>{{ yerler.length }} gezilecek yer</span>
            <span v-if="toplamSure">· yaklaşık {{ sureYaz(toplamSure) }} gezi</span>
          </div>
        </div>

        <NuxtLink :to="{ path: '/seyahatler/yeni', query: { destination: sehir.name } }" class="v-buton">✈ Bu şehre seyahat planla</NuxtLink>

        <a
          v-if="foto?.page_url"
          :href="foto.page_url"
          target="_blank"
          rel="noopener"
          class="foto-kaynak"
        >
          Fotoğraf: Vikipedi
        </a>
      </header>

      <!-- Gezilecek yerler -->
      <section class="bolum">
        <div class="bolum-ust">
          <h2 class="v-baslik">Gezilecek yerler</h2>
          <div class="kategori-seridi">
            <button
              type="button"
              class="v-cip"
              :class="{ aktif: secilenKategori === 'hepsi' }"
              @click="secilenKategori = 'hepsi'"
            >
              Tümü
            </button>
            <button
              v-for="k in kategoriler"
              :key="k.deger"
              type="button"
              class="v-cip"
              :class="{ aktif: secilenKategori === k.deger }"
              @click="secilenKategori = k.deger"
            >
              {{ k.ikon }} {{ k.ad }}
            </button>
          </div>
        </div>

        <p v-if="!filtrelenmis.length" class="durum">Bu kategoride yer yok.</p>

        <div class="yer-izgara">
          <article v-for="yer in filtrelenmis" :key="yer.id" class="yer-kart v-kart">
            <span class="yer-ikon" aria-hidden="true">{{ kategoriBilgisi(yer.category)?.ikon ?? '📍' }}</span>
            <div class="yer-yazi">
              <h3>{{ yer.name }}</h3>
              <span class="yer-kategori">{{ kategoriBilgisi(yer.category)?.ad ?? 'Diğer' }}</span>
              <div class="yer-bilgi">
                <span>⏱ {{ yer.visit_duration ? sureYaz(yer.visit_duration) : 'Süre bilinmiyor' }}</span>
                <span>🎟 {{ ucretYaz(yer) }}</span>
              </div>
            </div>
            <button
              v-if="haritadaOlanYerler.includes(yer.id)"
              type="button"
              class="harita-link"
              @click="haritadaGoster(yer.id)"
            >
              Haritada gör
            </button>
          </article>
        </div>
      </section>

      <!-- B'nin bileşenleri -->
      <section id="harita" class="bolum bilesen v-kart">
        <SehirHaritasi
          :city-id="sehir.id"
          :selected-place-id="secilenYerId"
          @konumlar-yuklendi="haritadaOlanYerler = $event"
        />
      </section>

      <section class="bolum bilesen v-kart">
        <GunlukGeziPlani :key="sehir.id" :city-name="sehir.name" :places="yerler" />
      </section>

      <section class="bolum bilesen v-kart">
        <RotaPaneli :key="sehir.id" :city-id="sehir.id" />
      </section>
    </template>
  </div>
</template>

<style scoped>
.sehir-sayfa {
  padding-top: 24px;
}

.geri {
  display: inline-block;
  margin-bottom: 18px;
  color: var(--v-muted);
  font-size: 14px;
  font-weight: 700;
  text-decoration: none;
}

.geri:hover {
  color: var(--v-ink);
}

.durum {
  color: var(--v-muted);
}

.durum.hata {
  color: var(--v-pink-deep);
}

.sehir-baslik {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  min-height: 240px;
  padding: clamp(28px, 4vw, 48px);
  border-radius: 28px;
}

.sehir-baslik {
  position: relative;
  background-position: center;
  background-size: cover;
}

.sehir-baslik.fotolu {
  min-height: 380px;
  color: white;
}

.sehir-baslik.fotolu .v-ust-yazi,
.sehir-baslik.fotolu .ozet {
  color: rgba(255, 255, 255, 0.92);
}

.foto-kaynak {
  position: absolute;
  top: 14px;
  right: 18px;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.8);
  color: var(--v-muted);
  font-size: 11px;
  text-decoration: none;
}

.sehir-baslik h1 {
  margin: 8px 0 10px;
  font-family: var(--v-font-accent);
  font-size: clamp(40px, 6vw, 68px);
  font-weight: 400;
  letter-spacing: -1.5px;
  line-height: 1;
}

.ozet {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  color: #4c566b;
  font-weight: 700;
}

.bolum {
  margin-top: 40px;
}

.bolum-ust {
  display: grid;
  gap: 16px;
  margin-bottom: 22px;
}

.kategori-seridi {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  scrollbar-width: none;
}

.yer-izgara {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

.yer-kart {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 20px;
  border-radius: 20px;
  transition: transform 0.2s, box-shadow 0.2s;
}

.yer-kart:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 30px rgba(77, 86, 140, 0.12);
}

.yer-ikon {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 14px;
  background: #f3eefb;
  font-size: 20px;
}

.yer-yazi h3 {
  margin: 0 0 2px;
  font-size: 16px;
}

.yer-kategori {
  color: var(--v-lilac-deep);
  font-size: 13px;
  font-weight: 700;
}

.yer-bilgi {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 10px;
  color: var(--v-muted);
  font-size: 13px;
}

.harita-link {
  align-self: flex-start;
  margin-top: auto;
  padding: 0;
  border: 0;
  background: none;
  color: var(--v-ink);
  font: inherit;
  font-size: 13px;
  font-weight: 800;
  text-decoration: underline;
  cursor: pointer;
}

.bilesen {
  padding: clamp(18px, 3vw, 30px);
}

.bilesen > .v-baslik {
  margin-bottom: 16px;
}
</style>
