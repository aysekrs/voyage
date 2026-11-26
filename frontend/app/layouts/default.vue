<script setup lang="ts">
import AppHeader from '~/components/AppHeader.vue'
</script>

<template>
  <div class="site">
    <AppHeader />

    <main class="site-govde">
      <slot />
    </main>

    <footer class="site-alt">
      <div class="kap alt-ic">
        <span>© {{ new Date().getFullYear() }} VoyageAI · Bitirme projesi</span>
        <span>Şehir fotoğrafları: Vikipedi / Wikimedia Commons</span>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.site {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  min-height: 100dvh;
}

.site-govde {
  flex: 1;
}

.site-alt {
  margin-top: 56px;
  border-top: 1px solid #eeecf4;
  background: rgba(255, 255, 255, 0.7);
}

.alt-ic {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 8px;
  padding-top: 22px;
  padding-bottom: 22px;
  color: var(--v-soft);
  font-size: 13px;
}
</style>
