<script setup lang="ts">
// Bütün sayfalarda aynı üst bar (Airbnb tarzı sade, yapışkan)
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import ProfileModal from './ProfileModal.vue'
import ActiveSessionsModal from './ActiveSessionsModal.vue'
import AuditLogsModal from './AuditLogsModal.vue'

const route = useRoute()
const { kullanici, kontrolEdildi, yenile, cikisYap } = useKullanici()

const menuAcik = ref(false)
const profilAcik = ref(false)
const oturumlarAcik = ref(false)
const loglarAcik = ref(false)
const menuKutusu = ref<HTMLElement | null>(null)

function disariTiklandi(olay: MouseEvent) {
  if (menuKutusu.value && !menuKutusu.value.contains(olay.target as Node)) {
    menuAcik.value = false
  }
}

function pencereAc(hangi: 'profil' | 'oturumlar' | 'loglar') {
  menuAcik.value = false
  if (hangi === 'profil') profilAcik.value = true
  if (hangi === 'oturumlar') oturumlarAcik.value = true
  if (hangi === 'loglar') loglarAcik.value = true
}

async function cikis() {
  menuAcik.value = false
  await cikisYap()
}

onMounted(() => {
  yenile()
  document.addEventListener('click', disariTiklandi)
})

onBeforeUnmount(() => document.removeEventListener('click', disariTiklandi))

// Sayfa değişince menüyü kapat ve oturumu tazele (giriş/çıkış sonrası)
watch(() => route.fullPath, () => {
  menuAcik.value = false
  yenile()
})
</script>

<template>
  <header class="ust-bar">
    <div class="kap ust-ic">
      <NuxtLink to="/" class="marka" aria-label="VoyageAI ana sayfa">
        <span class="marka-yildiz" aria-hidden="true">✦</span>
        <span>Voyage<em>AI</em></span>
      </NuxtLink>

      <nav class="orta-nav" aria-label="Ana menü">
        <NuxtLink to="/" class="nav-link" :class="{ aktif: route.path === '/' || route.path.startsWith('/sehir') }">
          Keşfet
        </NuxtLink>
        <NuxtLink to="/oneriler" class="nav-link" :class="{ aktif: route.path === '/oneriler' }">
          Bana öner
        </NuxtLink>
        <NuxtLink to="/seyahatler" class="nav-link" :class="{ aktif: route.path.startsWith('/seyahatler') }">
          Seyahatlerim
        </NuxtLink>
      </nav>

      <div class="sag">
        <NuxtLink v-if="kullanici" to="/seyahatler/yeni" class="yeni-link">
          + Yeni seyahat
        </NuxtLink>

        <NuxtLink
          v-if="kontrolEdildi && !kullanici && route.path !== '/login'"
          to="/login"
          class="giris-buton"
        >
          Giriş yap
        </NuxtLink>

        <div v-if="kullanici" ref="menuKutusu" class="menu-kutu">
          <button
            type="button"
            class="kullanici-hap"
            :aria-expanded="menuAcik"
            aria-haspopup="menu"
            @click.stop="menuAcik = !menuAcik"
          >
            <span class="hap-cizgi" aria-hidden="true">☰</span>
            <span class="avatar">{{ kullanici[0]?.toUpperCase() }}</span>
          </button>

          <transition name="menu">
            <div v-if="menuAcik" class="acilir-menu" role="menu">
              <p class="menu-kim">
                <span>Giriş yapan</span>
                <strong>{{ kullanici }}</strong>
              </p>
              <NuxtLink to="/" class="menu-oge mobil" role="menuitem">Keşfet</NuxtLink>
              <NuxtLink to="/oneriler" class="menu-oge mobil" role="menuitem">Bana öner</NuxtLink>
              <NuxtLink to="/seyahatler" class="menu-oge" role="menuitem">Seyahatlerim</NuxtLink>
              <NuxtLink to="/seyahatler/yeni" class="menu-oge" role="menuitem">Yeni seyahat</NuxtLink>
              <hr>
              <button type="button" class="menu-oge" role="menuitem" @click="pencereAc('profil')">Profil ayarları</button>
              <button type="button" class="menu-oge" role="menuitem" @click="pencereAc('oturumlar')">Aktif oturumlar</button>
              <button type="button" class="menu-oge" role="menuitem" @click="pencereAc('loglar')">Güvenlik kayıtları</button>
              <hr>
              <button type="button" class="menu-oge cikis" role="menuitem" @click="cikis">Çıkış yap</button>
            </div>
          </transition>
        </div>
      </div>
    </div>

    <ProfileModal v-model="profilAcik" />
    <ActiveSessionsModal v-model="oturumlarAcik" @all-revoked="cikis" />
    <AuditLogsModal v-model="loglarAcik" />
  </header>
</template>

<style scoped>
.ust-bar {
  position: sticky;
  top: 0;
  z-index: 50;
  border-bottom: 1px solid #eeecf4;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(14px);
}

.ust-ic {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 16px;
  height: 74px;
}

.marka {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  justify-self: start;
  color: var(--v-ink);
  font-family: var(--v-font-accent);
  font-size: 25px;
  font-weight: 700;
  letter-spacing: -0.8px;
  text-decoration: none;
}

.marka em {
  color: var(--v-lilac-deep);
  font-weight: 400;
}

.marka-yildiz {
  color: var(--v-lilac);
  font-family: var(--v-font);
  font-size: 17px;
}

.orta-nav {
  display: flex;
  gap: 6px;
}

.nav-link {
  padding: 10px 16px;
  border-radius: 999px;
  color: var(--v-muted);
  font-size: 15px;
  font-weight: 700;
  text-decoration: none;
  transition: background 0.2s, color 0.2s;
}

.nav-link:hover {
  background: var(--v-surface-soft);
  color: var(--v-ink);
}

.nav-link.aktif {
  color: var(--v-ink);
  box-shadow: inset 0 -2px 0 var(--v-lilac);
  border-radius: 0;
}

.sag {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.yeni-link {
  padding: 10px 14px;
  border-radius: 999px;
  color: var(--v-ink);
  font-size: 14px;
  font-weight: 700;
  text-decoration: none;
}

.yeni-link:hover {
  background: var(--v-surface-soft);
}

.giris-buton {
  padding: 10px 20px;
  border-radius: 999px;
  background: var(--v-gradient-button);
  color: white;
  font-size: 14px;
  font-weight: 800;
  text-decoration: none;
  box-shadow: 0 8px 18px rgba(133, 114, 183, 0.22);
}

.menu-kutu {
  position: relative;
}

.kullanici-hap {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 5px 5px 5px 14px;
  border: 1px solid #e3e1ec;
  border-radius: 999px;
  background: white;
  color: var(--v-muted);
  cursor: pointer;
  transition: box-shadow 0.2s;
}

.kullanici-hap:hover {
  box-shadow: 0 4px 14px rgba(77, 86, 140, 0.14);
}

.hap-cizgi {
  font-size: 15px;
}

.avatar {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--v-gradient-button);
  color: white;
  font-size: 14px;
  font-weight: 800;
}

.acilir-menu {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  width: 240px;
  padding: 8px 0;
  border: 1px solid #eeecf4;
  border-radius: 16px;
  background: white;
  box-shadow: 0 16px 40px rgba(41, 48, 66, 0.14);
}

.menu-kim {
  display: grid;
  gap: 2px;
  margin: 0;
  padding: 8px 18px 10px;
}

.menu-kim span {
  color: var(--v-soft);
  font-size: 12px;
}

.menu-kim strong {
  overflow: hidden;
  color: var(--v-ink);
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.menu-oge {
  display: block;
  width: 100%;
  padding: 11px 18px;
  border: 0;
  background: none;
  color: var(--v-ink);
  font: inherit;
  font-size: 14px;
  text-align: left;
  text-decoration: none;
  cursor: pointer;
}

.menu-oge:hover {
  background: var(--v-surface-soft);
}

.menu-oge.mobil {
  display: none;
}

.menu-oge.cikis {
  color: var(--v-pink-deep);
}

.acilir-menu hr {
  margin: 6px 0;
  border: 0;
  border-top: 1px solid #eeecf4;
}

.menu-enter-active,
.menu-leave-active {
  transition: opacity 0.15s, transform 0.15s;
}

.menu-enter-from,
.menu-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

@media (max-width: 760px) {
  .ust-ic {
    grid-template-columns: auto 1fr;
    height: 64px;
  }

  .orta-nav {
    display: none;
  }

  .yeni-link {
    display: none;
  }

  .menu-oge.mobil {
    display: block;
  }
}
</style>
