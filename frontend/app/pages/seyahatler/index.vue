<script setup lang="ts">
// Seyahatlerim: giriş gerekir
import SeyahatListesi from '~/components/SeyahatListesi.vue'

const { kullanici, yenile } = useKullanici()

onMounted(async () => {
  if (!(kullanici.value ?? (await yenile()))) {
    await navigateTo({ path: '/login', query: { redirect: '/seyahatler' } })
  }
})
</script>

<template>
  <div class="kap sayfa-ic">
    <div v-if="kullanici" class="ust-satir">
      <NuxtLink to="/seyahatler/yeni" class="v-buton">+ Yeni seyahat</NuxtLink>
    </div>
    <SeyahatListesi v-if="kullanici" />
  </div>
</template>

<style scoped>
.sayfa-ic {
  padding-top: 28px;
}

.ust-satir {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 18px;
}
</style>
