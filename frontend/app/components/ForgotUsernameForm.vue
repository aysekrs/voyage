<template>
  <form id="form-kullanici-hatirla" @submit.prevent="kullaniciAdiHatirla" class="form">
    <div class="dogrulama-bilgi">
      <span class="dogrulama-ikon">👤</span>
      <p>Kayıtlı e-posta adresinize kullanıcı adınızı gönderelim.</p>
    </div>
    <div class="alan">
      <label>E-posta</label>
      <input
        id="hatirla-email"
        v-model="email"
        type="email"
        placeholder="ornek@mail.com"
        autocomplete="email"
        required
      />
    </div>
    <button id="btn-kullanici-hatirla" type="submit" class="btn btn-mavi" :disabled="islem">
      {{ islem ? 'Gönderiliyor…' : 'Kullanıcı Adımı Gönder →' }}
    </button>
    <button type="button" class="btn btn-geri" @click="$emit('close')">
      ← Giriş Yap'a Dön
    </button>
  </form>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits(['success', 'error', 'close'])

const email = ref('')
const islem = ref(false)

function hataMesajiniAl(e: unknown): string {
  if (e && typeof e === 'object' && 'data' in e) {
    const data = (e as { data?: { message?: string } }).data
    if (data?.message) return data.message
  }
  if (e instanceof Error) return e.message
  return 'Beklenmedik bir hata oluştu.'
}

async function kullaniciAdiHatirla() {
  islem.value = true
  emit('error', '')
  try {
    const veri = await $fetch<{ message: string }>('/api/kullanici-adi-hatirla', {
      method: 'POST',
      body: { email: email.value },
    })
    emit('success', veri.message)
    email.value = ''
    setTimeout(() => {
      emit('close')
    }, 4000)
  } catch (e) {
    emit('error', hataMesajiniAl(e))
  } finally {
    islem.value = false
  }
}
</script>

<style scoped>
.btn-mavi {
  background: linear-gradient(135deg, #789bd6, #8e89c4);
  color: #fff;
  box-shadow: 0 4px 20px rgba(59, 130, 246, 0.3);
  margin-top: 4px;
}

.btn-mavi:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 25px rgba(59, 130, 246, 0.45);
}

.btn-mavi:not(:disabled):active { transform: translateY(0); }
.btn-mavi:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
