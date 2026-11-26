<script setup lang="ts">
// Tek seyahatin sayfası: özet + sekmeler (şehir seç, uçuşlar, konaklama)
import SeyahatDetay from '~/components/SeyahatDetay.vue'

const route = useRoute()
const tripId = Number(route.params.id)
const { kullanici, yenile } = useKullanici()

onMounted(async () => {
  if (!(kullanici.value ?? (await yenile()))) {
    await navigateTo({ path: '/login', query: { redirect: route.fullPath } })
  }
})
</script>

<template>
  <div class="kap sayfa-ic">
    <NuxtLink to="/seyahatler" class="geri">← Seyahatlerim</NuxtLink>
    <SeyahatDetay v-if="kullanici" :trip-id="tripId" @kapat="navigateTo('/seyahatler')" />
  </div>
</template>

<style scoped>
.sayfa-ic {
  padding-top: 24px;
}

.geri {
  display: inline-block;
  margin-bottom: 8px;
  color: var(--v-muted);
  font-size: 14px;
  font-weight: 700;
  text-decoration: none;
}

.geri:hover {
  color: var(--v-ink);
}
</style>
