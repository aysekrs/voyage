<template>
  <button
    type="button"
    class="theme-toggle-btn group"
    @click="toggleTheme"
    :title="isDark ? 'Açık Moda Geç' : 'Koyu Moda Geç'"
  >
    <span v-if="isDark" class="btn-icerik">
      <span class="ikon">☀️</span>
      <span class="metin">Açık Mod</span>
    </span>
    <span v-else class="btn-icerik">
      <span class="ikon">🌙</span>
      <span class="metin">Koyu Mod</span>
    </span>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: 'dark' }
})

const emit = defineEmits(['update:modelValue'])

const isDark = computed(() => props.modelValue === 'dark')

function toggleTheme() {
  const yeniTema = isDark.value ? 'light' : 'dark'
  emit('update:modelValue', yeniTema)
}
</script>

<style scoped>
.üst-kontrol-grup {
  display: flex;
  align-items: center;
  gap: 10px;
}

.theme-toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 9999px;
  background: var(--card-bg, rgba(255, 255, 255, 0.12));
  backdrop-filter: blur(12px);
  border: 1px solid var(--card-border, rgba(255, 255, 255, 0.2));
  color: var(--text-main, #ffffff);
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.15);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.theme-toggle-btn:hover {
  transform: translateY(-2px) scale(1.03);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.22);
}

.theme-toggle-btn:active {
  transform: translateY(0) scale(0.97);
}

.btn-icerik {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.ikon {
  font-size: 1.1rem;
}

.metin {
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.3px;
}
</style>
