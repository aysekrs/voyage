<template>
  <div class="dashboard-container">
    <!-- ─── 1. Üst İnce Kullanıcı Barı ─────────────────────────────── -->
    <div class="ust-kullanici-bar">
      <div class="kullanici-etiket">
        <span class="user-avatar-kucuk">{{ avatarHarfi }}</span>
        <span class="user-email-metin">@{{ kullanici }}</span>
      </div>
      <div class="ust-btn-grup">
        <button type="button" class="ust-btn" @click="$emit('openProfile')" title="Profil Ayarları">⚙️ Profil</button>
        <button type="button" class="ust-btn" @click="$emit('openSessions')" title="Aktif Oturumlar">📱 Oturumlar</button>
        <button type="button" class="ust-btn" @click="$emit('openLogs')" title="Güvenlik Logları">📜 Loglar</button>
        <button type="button" class="ust-btn cikis-btn" @click="$emit('logout')" :disabled="islem" title="Çıkış Yap">🚪 Çıkış</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps({
  kullanici: { type: String, required: true },
  islem: { type: Boolean, default: false }
})

defineEmits(['openProfile', 'openSessions', 'openLogs', 'logout'])

const avatarHarfi = computed(() => {
  return props.kullanici ? props.kullanici[0].toUpperCase() : 'U'
})
</script>

<style scoped>
.dashboard-container {
  width: 100%;
  max-width: 1100px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 10px;
}

/* Üst Kullanıcı Barı */
.ust-kullanici-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--card-bg, #f6f4fb);
  backdrop-filter: blur(12px);
  border: 1px solid var(--card-border, #e5e7f0);
  border-radius: 16px;
  padding: 10px 16px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  flex-wrap: wrap;
  gap: 10px;
}

.kullanici-etiket {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-avatar-kucuk {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #8e89c4 0%, #b6a4da 100%);
  color: #ffffff;
  font-size: 0.95rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-email-metin {
  font-size: 0.88rem;
  font-weight: 700;
  color: var(--text-main, #293042);
}

.ust-btn-grup {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ust-btn {
  background: #efecf7;
  border: 1px solid #e5e7f0;
  color: var(--text-main, #ffffff);
  font-size: 0.78rem;
  font-weight: 600;
  padding: 6px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.ust-btn:hover {
  background: #efecf7;
  transform: translateY(-1px);
}

.ust-btn.cikis-btn {
  background: rgba(180, 95, 123, 0.12);
  border-color: rgba(180, 95, 123, 0.25);
  color: #b45f7b;
}

.ust-btn.cikis-btn:hover {
  background: rgba(180, 95, 123, 0.25);
}
</style>
