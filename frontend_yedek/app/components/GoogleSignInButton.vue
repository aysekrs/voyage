<template>
  <div class="google-btn-container">
    <div id="google-signin-btn-ref" class="google-btn-wrapper"></div>
    <button
      v-if="!googleReady"
      type="button"
      class="btn btn-google-fallback"
      :disabled="yukleniyor"
      @click="googleGirisBaslat"
    >
      <svg class="google-icon" viewBox="0 0 24 24">
        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
      </svg>
      <span>{{ yukleniyor ? 'Giriş Yapılıyor…' : 'Google ile Giriş Yap' }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const emit = defineEmits(['success', 'error'])

const config = useRuntimeConfig()
const googleReady = ref(false)
const yukleniyor = ref(false)
const clientId = config.public.googleClientId || '928509312019-demo.apps.googleusercontent.com'

onMounted(() => {
  sdkYukle()
})

function sdkYukle() {
  if (typeof window === 'undefined') return
  if (document.getElementById('google-gsi-script')) {
    initGoogle()
    return
  }

  const script = document.createElement('script')
  script.id = 'google-gsi-script'
  script.src = 'https://accounts.google.com/gsi/client'
  script.async = true
  script.defer = true
  script.onload = () => initGoogle()
  document.head.appendChild(script)
}

function initGoogle() {
  if (!(window as unknown as { google?: { accounts?: { id?: unknown } } }).google?.accounts?.id) return

  try {
    const googleObj = (window as unknown as { google: { accounts: { id: { initialize: (c: unknown) => void; renderButton: (el: HTMLElement, opts: unknown) => void } } } }).google

    googleObj.accounts.id.initialize({
      client_id: clientId,
      callback: handleCredentialResponse,
      auto_select: false,
    })

    const wrapper = document.getElementById('google-signin-btn-ref')
    if (wrapper) {
      googleObj.accounts.id.renderButton(wrapper, {
        theme: 'filled_dark',
        size: 'large',
        width: '100%',
        text: 'continue_with',
        shape: 'pill',
      })
      googleReady.value = true
    }
  } catch (e) {
    console.warn('[Google SDK] Yükleme uyarısı:', e)
  }
}

async function handleCredentialResponse(response: { credential?: string }) {
  if (!response?.credential) return
  yukleniyor.value = true
  try {
    const res = await $fetch<{ success: boolean; kullanici: string; message: string }>('/api/auth/google', {
      method: 'POST',
      body: { credential: response.credential },
    })
    emit('success', res)
  } catch (err: unknown) {
    const msg = (err as { data?: { message?: string } })?.data?.message || 'Google girişi başarısız.'
    emit('error', msg)
  } finally {
    yukleniyor.value = false
  }
}

function googleGirisBaslat() {
  const googleObj = (window as unknown as { google?: { accounts?: { id?: { prompt: () => void } } } }).google
  if (googleObj?.accounts?.id?.prompt) {
    googleObj.accounts.id.prompt()
  } else {
    emit('error', 'Google SDK henüz hazır değil. Lütfen birkaç saniye bekleyin veya sayfayı yenileyin.')
  }
}
</script>

<style scoped>
.google-btn-container {
  width: 100%;
  margin: 12px 0;
}

.google-btn-wrapper {
  width: 100%;
  display: flex;
  justify-content: center;
}

.btn-google-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background: #ffffff;
  color: #3c4043;
  border: 1px solid #dadce0;
  border-radius: 10px;
  padding: 11px 16px;
  font-size: 0.92rem;
  font-weight: 600;
  cursor: pointer;
  width: 100%;
  transition: background-color 0.2s, box-shadow 0.2s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.btn-google-fallback:hover {
  background: #f8f9fa;
  border-color: #d2e3fc;
  box-shadow: 0 2px 6px rgba(60, 64, 67, 0.15);
}

.google-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}
</style>
