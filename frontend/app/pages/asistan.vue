<script setup lang="ts">
// 5. hafta (Kişi B): AI asistanla seyahat oluşturma
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
    <header class="asistan-baslik">
      <span class="v-ust-yazi">AI asistan</span>
      <h1>Seyahatini anlat, <em>gerisini birlikte planlayalım.</em></h1>
      <p>
        Nereden, ne zaman, kaç kişi ve hangi bütçeyle gitmek istediğini yaz.
        Anladıklarımı yanda gösteririm; onaylayınca seyahatin oluşur.
      </p>
    </header>

    <AiSohbet v-if="kullanici" @olusturuldu="id => navigateTo(`/seyahatler/${id}`)" />
  </div>
</template>

<style scoped>
.sayfa-ic {
  padding-top: 28px;
  padding-bottom: 48px;
}

.asistan-baslik {
  padding: clamp(28px, 4vw, 52px);
  border-radius: 28px;
  background: var(--v-gradient-soft);
}

.asistan-baslik h1 {
  max-width: 720px;
  margin: 12px 0;
  font-size: clamp(30px, 4vw, 48px);
  font-weight: 800;
  letter-spacing: -1.4px;
  line-height: 1.1;
}

.asistan-baslik h1 em {
  color: var(--v-lilac-deep);
  font-family: var(--v-font-accent);
  font-weight: 400;
}

.asistan-baslik p {
  max-width: 580px;
  margin: 0;
  color: #5f6a82;
  line-height: 1.7;
}
</style>
