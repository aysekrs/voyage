<script setup lang="ts">
// Yeni seyahat: arama çubuğundan gelen bilgiler formu ön doldurur
import SeyahatOlustur from '~/components/SeyahatOlustur.vue'

const route = useRoute()
const { kullanici, yenile } = useKullanici()

onMounted(async () => {
  if (!(kullanici.value ?? (await yenile()))) {
    await navigateTo({ path: '/login', query: { redirect: route.fullPath } })
  }
})
</script>

<template>
  <div class="kap sayfa-ic">
    <SeyahatOlustur v-if="kullanici" @olusturuldu="id => navigateTo(`/seyahatler/${id}`)" />
  </div>
</template>

<style scoped>
.sayfa-ic {
  padding-top: 28px;
}
</style>
