<script setup lang="ts">
// Keşfet: Airbnb tarzı arama çubuğu + kategori şeridi + şehir kartları
import { computed, onMounted, reactive, ref, watch } from 'vue'

interface Sehir {
  id: number
  name: string
  country: string
  place_count: number
  categories: Record<'history' | 'nature' | 'food' | 'nightlife', number>
}

const { kullanici, yenile } = useKullanici()
const { fotolar, getir: fotoGetir } = useSehirFotografi()

const sehirler = ref<Sehir[]>([])
const yukleniyor = ref(true)
const hata = ref('')
const secilenKategori = ref<string>('hepsi')
const aramaMetni = ref('')
const KART_SAYISI = 12
const hepsiniGoster = ref(false)

const arama = reactive({
  origin_city: '',
  start_date: '',
  end_date: '',
  people_count: 2,
  budget_try: 40000
})

const bugun = new Date().toISOString().slice(0, 10)

const filtrelenmis = computed(() => {
  const metin = aramaMetni.value.trim().toLocaleLowerCase('tr')
  let liste = sehirler.value.filter(s => s.place_count > 0)

  if (metin) {
    liste = liste.filter(s =>
      `${s.name} ${s.country}`.toLocaleLowerCase('tr').includes(metin)
    )
  }

  if (secilenKategori.value !== 'hepsi') {
    const k = secilenKategori.value as keyof Sehir['categories']
    liste = liste
      .filter(s => s.categories[k] > 0)
      .sort((a, b) => b.categories[k] - a.categories[k])
  }

  return liste
})

const gorunenler = computed(() =>
  hepsiniGoster.value ? filtrelenmis.value : filtrelenmis.value.slice(0, KART_SAYISI)
)

// Ekranda görünen kartların fotoğraflarını getir
watch(gorunenler, liste => liste.forEach(s => fotoGetir(s.id, s.name, s.country)), { immediate: true })

function baskinKategori(s: Sehir) {
  return [...kategoriler].sort((a, b) => s.categories[b.anahtar] - s.categories[a.anahtar])[0]!
}

async function planla() {
  const sorgu: Record<string, string> = {}
  for (const [anahtar, deger] of Object.entries(arama)) {
    if (deger !== '' && deger !== null) sorgu[anahtar] = String(deger)
  }
  const hedef = { path: '/seyahatler/yeni', query: sorgu }

  const girisli = kullanici.value ?? (await yenile())
  if (girisli) {
    await navigateTo(hedef)
  } else {
    await navigateTo({
      path: '/login',
      query: { redirect: useRouter().resolve(hedef).fullPath }
    })
  }
}

onMounted(async () => {
  try {
    sehirler.value = await $fetch<Sehir[]>('/api/kesfet')
  } catch {
    hata.value = 'Şehirler yüklenemedi. Backend çalışıyor mu?'
  } finally {
    yukleniyor.value = false
  }
})
</script>

<template>
  <div>
    <!-- Karşılama + arama -->
    <section class="kap kahraman">
      <div class="kahraman-arka" aria-hidden="true">
        <span class="gunes"></span>
        <span class="ucak">✈</span>
        <span class="yol"></span>
        <span class="tepe tepe-arka"></span>
        <span class="tepe tepe-on"></span>
      </div>

      <div class="kahraman-yazi">
        <span class="v-ust-yazi">Yapay zekâ destekli seyahat planlayıcı</span>
        <h1>Dünyayı keşfet, <em>seyahatini planla.</em></h1>
        <p>
          Bütçeni ve ilgi alanlarını söyle; sana uygun şehirleri, uçuşları,
          otelleri ve gün gün rotanı birlikte çıkaralım.
        </p>
      </div>

      <form class="arama-cubugu" @submit.prevent="planla">
        <label class="arama-alan">
          <span>Nereden</span>
          <select v-model="arama.origin_city">
            <option value="">Kalkış şehri</option>
            <option v-for="(_, sehir) in havalimanlari" :key="sehir" :value="sehir">
              {{ sehir }}
            </option>
          </select>
        </label>

        <label class="arama-alan">
          <span>Gidiş</span>
          <input v-model="arama.start_date" type="date" :min="bugun">
        </label>

        <label class="arama-alan">
          <span>Dönüş</span>
          <input v-model="arama.end_date" type="date" :min="arama.start_date || bugun">
        </label>

        <label class="arama-alan dar">
          <span>Kişi</span>
          <input v-model.number="arama.people_count" type="number" min="1" max="20">
        </label>

        <label class="arama-alan">
          <span>Bütçe (TL)</span>
          <input v-model.number="arama.budget_try" type="number" min="1" step="1000">
        </label>

        <button type="submit" class="arama-buton" aria-label="Seyahati planla">
          <span aria-hidden="true">✈</span>
          <span class="buton-yazi">Planla</span>
        </button>
      </form>
    </section>

    <!-- Kategori şeridi -->
    <section class="kap kesfet">
      <div class="kesfet-ust">
        <div>
          <span class="v-ust-yazi">Keşfet</span>
          <h2 class="v-baslik">İlham veren şehirler</h2>
        </div>

        <label class="sehir-ara">
          <span aria-hidden="true">⌕</span>
          <input v-model="aramaMetni" type="search" placeholder="Şehir ya da ülke ara">
        </label>
      </div>

      <div class="kategori-seridi" role="tablist" aria-label="Kategoriler">
        <button
          type="button"
          class="v-cip"
          :class="{ aktif: secilenKategori === 'hepsi' }"
          @click="secilenKategori = 'hepsi'"
        >
          ✦ Tümü
        </button>
        <button
          v-for="k in kategoriler"
          :key="k.anahtar"
          type="button"
          class="v-cip"
          :class="{ aktif: secilenKategori === k.anahtar }"
          @click="secilenKategori = k.anahtar"
        >
          {{ k.ikon }} {{ k.ad }}
        </button>
      </div>

      <p v-if="yukleniyor" class="durum">Şehirler yükleniyor…</p>
      <p v-else-if="hata" class="durum hata">{{ hata }}</p>
      <p v-else-if="!filtrelenmis.length" class="durum">Aramana uygun şehir bulunamadı.</p>

      <div class="sehir-izgara">
        <NuxtLink
          v-for="sehir in gorunenler"
          :key="sehir.id"
          :to="`/sehir/${sehir.id}`"
          class="sehir-kart"
        >
          <div class="kart-gorsel" :style="{ background: sehirGecisi(sehir.id) }">
            <img
              v-if="fotolar[sehir.id]?.url"
              :src="fotolar[sehir.id]!.url!"
              :alt="`${sehir.name} fotoğrafı`"
              class="kart-foto"
              loading="lazy"
            >
            <span v-else class="kart-harf" aria-hidden="true">{{ sehir.name[0] }}</span>
            <span class="kart-ikon" aria-hidden="true">{{ baskinKategori(sehir).ikon }}</span>
          </div>

          <div class="kart-yazi">
            <div class="kart-satir">
              <strong>{{ sehir.name }}</strong>
              <span class="yer-sayisi">{{ sehir.place_count }} yer</span>
            </div>
            <span class="ulke">{{ sehir.country }}</span>
            <div class="kart-etiketler">
              <span
                v-for="k in kategoriler.filter(k => sehir.categories[k.anahtar] > 0)"
                :key="k.anahtar"
              >
                {{ k.ikon }} {{ sehir.categories[k.anahtar] }}
              </span>
            </div>
          </div>
        </NuxtLink>
      </div>

      <div v-if="filtrelenmis.length > KART_SAYISI" class="daha-fazla">
        <button type="button" class="v-buton-ikincil" @click="hepsiniGoster = !hepsiniGoster">
          {{ hepsiniGoster ? 'Daha az göster' : `Tüm şehirleri göster (${filtrelenmis.length})` }}
        </button>
      </div>
    </section>

    <!-- Nasıl çalışır -->
    <section class="kap adimlar">
      <div class="adim v-kart">
        <span class="adim-no">1</span>
        <h3>Anlat</h3>
        <p>Nereden çıkacağını, bütçeni, tarihlerini ve neyi sevdiğini yaz.</p>
      </div>
      <div class="adim v-kart">
        <span class="adim-no">2</span>
        <h3>Karşılaştır</h3>
        <p>Her şehir için uçuş, otel, yemek ve aktivite dahil toplam maliyeti gör.</p>
      </div>
      <div class="adim v-kart">
        <span class="adim-no">3</span>
        <h3>Yola çık</h3>
        <p>Şehrini seç; gün gün rotan haritada hazır olsun.</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
/* ---------- Karşılama ---------- */
.kahraman {
  position: relative;
  margin-top: 28px;
  padding-top: clamp(44px, 6vw, 72px);
  padding-bottom: 0;
}

.kahraman-arka {
  position: absolute;
  inset: 0 clamp(16px, 4vw, 40px) 60px;
  z-index: -1;
  overflow: hidden;
  border-radius: 32px;
  background: var(--v-gradient-soft);
}

.gunes {
  position: absolute;
  top: 46px;
  right: 14%;
  width: 140px;
  height: 140px;
  border-radius: 50%;
  background: #f9cfdb;
}

.ucak {
  position: absolute;
  top: 70px;
  right: 25%;
  color: #7c86bb;
  font-size: 52px;
  transform: rotate(-18deg);
}

.yol {
  position: absolute;
  top: 140px;
  right: 31%;
  width: 120px;
  height: 64px;
  border-bottom: 2px dashed #a9a1d4;
  border-radius: 50%;
  transform: rotate(20deg);
}

.tepe {
  position: absolute;
  width: 60%;
  height: 200px;
  border-radius: 50% 50% 0 0;
}

.tepe-arka {
  right: -8%;
  bottom: -110px;
  transform: rotate(-8deg);
  background: #c9bdea;
}

.tepe-on {
  right: -20%;
  bottom: -130px;
  transform: rotate(8deg);
  background: #b4c7ec;
}

.kahraman-yazi {
  max-width: 640px;
  padding-inline: clamp(24px, 5vw, 64px);
}

.kahraman-yazi h1 {
  margin: 14px 0 14px;
  font-size: clamp(34px, 5vw, 60px);
  font-weight: 800;
  letter-spacing: -2px;
  line-height: 1.05;
}

.kahraman-yazi h1 em {
  color: var(--v-lilac-deep);
  font-family: var(--v-font-accent);
  font-weight: 400;
  letter-spacing: -1px;
}

.kahraman-yazi p {
  max-width: 520px;
  margin: 0;
  color: #5f6a82;
  font-size: 16px;
  line-height: 1.7;
}

/* ---------- Arama çubuğu ---------- */
.arama-cubugu {
  display: flex;
  align-items: center;
  max-width: 980px;
  margin: 40px auto 0;
  padding: 8px 8px 8px 12px;
  border: 1px solid #ebe8f3;
  border-radius: 999px;
  background: white;
  box-shadow: 0 16px 44px rgba(77, 86, 140, 0.16);
}

.arama-alan {
  display: flex;
  flex: 1 1 0;
  flex-direction: column;
  min-width: 0;
  padding: 8px 18px;
  border-radius: 999px;
  cursor: pointer;
  transition: background 0.2s;
}

.arama-alan + .arama-alan {
  border-left: 1px solid #eeecf4;
}

.arama-alan:hover {
  background: var(--v-surface-soft);
}

.arama-alan.dar {
  flex: 0.6 1 0;
}

.arama-alan span {
  color: var(--v-ink);
  font-size: 12px;
  font-weight: 800;
}

.arama-alan input,
.arama-alan select {
  width: 100%;
  min-width: 0;
  padding: 2px 0 0;
  border: 0;
  background: transparent;
  color: var(--v-muted);
  font: inherit;
  font-size: 14px;
  box-shadow: none;
  appearance: none;
}

.arama-alan input:focus,
.arama-alan select:focus {
  box-shadow: none;
}

.arama-buton {
  display: inline-flex;
  flex: none;
  align-items: center;
  gap: 8px;
  height: 52px;
  padding: 0 24px;
  border: 0;
  border-radius: 999px;
  background: var(--v-gradient-button);
  box-shadow: 0 10px 22px rgba(133, 114, 183, 0.3);
  color: white;
  font: inherit;
  font-size: 16px;
  font-weight: 800;
  cursor: pointer;
  transition: transform 0.2s;
}

.arama-buton:hover {
  transform: scale(1.03);
}

/* ---------- Keşfet ---------- */
.kesfet {
  margin-top: 64px;
}

.kesfet-ust {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}

.sehir-ara {
  display: flex;
  align-items: center;
  gap: 8px;
  width: min(100%, 300px);
  padding: 10px 16px;
  border: 1px solid #e7e5ef;
  border-radius: 999px;
  background: white;
  color: var(--v-soft);
}

.sehir-ara input {
  width: 100%;
  border: 0;
  background: transparent;
  color: var(--v-ink);
  font: inherit;
  font-size: 14px;
  box-shadow: none;
}

.kategori-seridi {
  display: flex;
  gap: 10px;
  margin-bottom: 28px;
  padding-bottom: 4px;
  overflow-x: auto;
  scrollbar-width: none;
}

.durum {
  color: var(--v-muted);
}

.durum.hata {
  color: var(--v-pink-deep);
}

.sehir-izgara {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 28px 22px;
}

.sehir-kart {
  display: flex;
  flex-direction: column;
  gap: 12px;
  color: inherit;
  text-decoration: none;
}

.kart-gorsel {
  position: relative;
  aspect-ratio: 1 / 0.8;
  overflow: hidden;
  border-radius: 20px;
  transition: transform 0.25s, box-shadow 0.25s;
}

.sehir-kart:hover .kart-foto {
  transform: scale(1.04);
}

.kart-foto {
  transition: transform 0.4s ease;
}

.sehir-kart:hover .kart-gorsel {
  transform: translateY(-3px);
  box-shadow: 0 16px 34px rgba(77, 86, 140, 0.18);
}

.kart-foto {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  animation: belir 0.4s ease;
}

@keyframes belir {
  from { opacity: 0; }
  to { opacity: 1; }
}

.kart-ikon {
  position: absolute;
  z-index: 1;
  top: 14px;
  left: 14px;
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.85);
  font-size: 18px;
}

.kart-harf {
  position: absolute;
  right: 18px;
  bottom: 6px;
  color: rgba(255, 255, 255, 0.85);
  font-family: var(--v-font-accent);
  font-size: 96px;
  font-style: italic;
  line-height: 1;
}

.kart-yazi {
  display: grid;
  gap: 3px;
  padding: 0 2px;
}

.kart-satir {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}

.kart-satir strong {
  font-size: 16px;
}

.yer-sayisi {
  color: var(--v-muted);
  font-size: 13px;
  white-space: nowrap;
}

.ulke {
  color: var(--v-muted);
  font-size: 14px;
}

.kart-etiketler {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 4px;
  color: var(--v-soft);
  font-size: 12px;
}

.daha-fazla {
  display: flex;
  justify-content: center;
  margin-top: 36px;
}

/* ---------- Adımlar ---------- */
.adimlar {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 18px;
  margin-top: 72px;
}

.adim {
  padding: 26px;
}

.adim-no {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #f0ebfa;
  color: var(--v-lilac-deep);
  font-weight: 800;
}

.adim h3 {
  margin: 16px 0 6px;
  font-size: 18px;
}

.adim p {
  margin: 0;
  color: var(--v-muted);
  font-size: 14px;
  line-height: 1.6;
}

/* ---------- Mobil ---------- */
@media (max-width: 900px) {
  .arama-cubugu {
    flex-wrap: wrap;
    gap: 4px;
    border-radius: 26px;
    padding: 10px;
  }

  .arama-alan {
    flex: 1 1 40%;
    border-radius: 16px;
  }

  .arama-alan + .arama-alan {
    border-left: 0;
  }

  .arama-buton {
    flex: 1 1 100%;
    justify-content: center;
  }

  .adimlar {
    grid-template-columns: 1fr;
  }

  .kahraman-arka .gunes,
  .kahraman-arka .ucak,
  .kahraman-arka .yol {
    opacity: 0.35;
  }
}
</style>
