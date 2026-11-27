<script setup lang="ts">
// "Bana öner": B'nin ilgi alanına göre şehir öneren paneli (OneriPaneli)
interface Sehir {
  id: number
  name: string
  country: string
}

const hata = ref('')

async function sehriAc(ulke: string, sehirAdi: string) {
  hata.value = ''
  try {
    const sehirler = await $fetch<Sehir[]>('/api/kesfet')
    const bulunan = sehirler.find(s => s.country === ulke && s.name === sehirAdi)
    if (bulunan) {
      await navigateTo(`/sehir/${bulunan.id}`)
    } else {
      hata.value = `${sehirAdi} şehir listesinde bulunamadı.`
    }
  } catch {
    hata.value = 'Şehir sayfası açılamadı.'
  }
}
</script>

<template>
  <div class="kap sayfa-ic">
    <header class="oneri-baslik">
      <span class="v-ust-yazi">Bana öner</span>
      <h1>Nereye gideceğine <em>birlikte karar verelim.</em></h1>
      <p>
        Doğa, yemek, tarih ve gece hayatından hangisini ne kadar sevdiğini ayarla;
        sana en uygun şehirleri sıralayalım. Bir şehre tıklayınca detayları açılır.
      </p>
    </header>

    <p v-if="hata" class="hata">{{ hata }}</p>

    <div class="panel v-kart">
      <OneriPaneli @sehir-kesfet="sehriAc" />
    </div>
  </div>
</template>

<style scoped>
.sayfa-ic {
  padding-top: 28px;
}

.oneri-baslik {
  padding: clamp(28px, 4vw, 52px);
  border-radius: 28px;
  background: var(--v-gradient-soft);
}

.oneri-baslik h1 {
  max-width: 700px;
  margin: 12px 0;
  font-size: clamp(30px, 4vw, 48px);
  font-weight: 800;
  letter-spacing: -1.4px;
  line-height: 1.1;
}

.oneri-baslik h1 em {
  color: var(--v-lilac-deep);
  font-family: var(--v-font-accent);
  font-weight: 400;
}

.oneri-baslik p {
  max-width: 560px;
  margin: 0;
  color: #5f6a82;
  line-height: 1.7;
}

.hata {
  margin-top: 16px;
  color: var(--v-pink-deep);
}

.panel {
  margin-top: 24px;
  padding: clamp(8px, 2vw, 16px);
}

/* B'nin paneli kendi kartıyla geliyor; içte ikinci bir kart gibi durmasın */
.panel :deep(> section) {
  margin-top: 0;
  box-shadow: none;
}
</style>
