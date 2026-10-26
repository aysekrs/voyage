<template>
  <div>
    <!-- Şifre Sıfırlama — Adım 1: Email gir -->
    <form v-if="!form.kodAsamasi" id="form-sifre-baslat" @submit.prevent="sifreSifirlaBaslat" class="form">
      <div class="dogrulama-bilgi">
        <span class="dogrulama-ikon">🔑</span>
        <p>Email adresinize şifre sıfırlama kodu göndereceğiz.</p>
      </div>
      <div class="alan">
        <label>E-posta</label>
        <input
          id="sifre-email"
          v-model="form.email"
          type="email"
          placeholder="ornek@mail.com"
          autocomplete="email"
          required
        />
      </div>
      <button id="btn-sifre-baslat" type="submit" class="btn btn-turuncu" :disabled="islem">
        {{ islem ? 'Gönderiliyor…' : 'Kod Gönder →' }}
      </button>
      <button type="button" class="btn btn-geri" @click="$emit('close')">
        ← Giriş Yap
      </button>
    </form>

    <!-- Şifre Sıfırlama — Adım 2: Kod + Yeni Şifre -->
    <form v-else id="form-sifre-yenile" @submit.prevent="sifreYenile" class="form">
      <div class="dogrulama-bilgi">
        <span class="dogrulama-ikon">📧</span>
        <p>
  E-posta adresiniz sistemde kayıtlıysa
  <strong>{{ form.email }}</strong> adresine
  şifre sıfırlama kodu gönderilecektir.
</p>
      </div>
      <div class="alan">
        <label>6 Haneli Sıfırlama Kodu</label>
        <input
          id="sifre-kod"
          v-model="form.kod"
          type="text"
          inputmode="numeric"
          pattern="[0-9]{6}"
          placeholder="000000"
          maxlength="6"
          autocomplete="one-time-code"
          required
          class="kod-input"
        />
        <div class="resend-alan" style="text-align: center; margin-top: 12px; margin-bottom: 4px;">
          <button
            type="button"
            class="btn-link"
            :disabled="geriSayim > 0 || islem"
            @click="kodYenidenGonder"
            style="font-size: 0.8rem; text-decoration: underline;"
          >
            {{ geriSayim > 0 ? `Yeniden Kod Gönder (${geriSayim}s)` : 'Kodu Almadınız mı? Yeniden Gönder' }}
          </button>
        </div>
      </div>
      <div class="alan">
        <label>Yeni Şifre</label>
        <div class="sifre-alan">
          <input
            id="sifre-yeni"
            v-model="form.yeniSifre"
            :type="gozGoster ? 'text' : 'password'"
            placeholder="Min. 8 karakter, büyük+küçük harf"
            autocomplete="new-password"
            required
          />
          <button type="button" class="goz-btn" @click="gozGoster = !gozGoster" :title="gozGoster ? 'Şifreyi Gizle' : 'Şifreyi Göster'">
            <svg v-if="gozGoster" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
              <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
              <line x1="1" y1="1" x2="23" y2="23"/>
            </svg>
            <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
              <circle cx="12" cy="12" r="3"/>
            </svg>
          </button>
        </div>
        <!-- Şifre Gücü Göstergesi -->
        <div v-if="form.yeniSifre" class="sifre-gucu">
          <div class="guc-bar-arkaplan">
            <div class="guc-bar" :class="'seviye-' + sifirlaSifreAnaliz.toplam" :style="{ width: (sifirlaSifreAnaliz.toplam / 4) * 100 + '%' }"></div>
          </div>
          <ul class="guc-liste">
            <li :class="{ gecirli: sifirlaSifreAnaliz.uzunluk }">
              <span class="durum-ikon">{{ sifirlaSifreAnaliz.uzunluk ? '✓' : '○' }}</span>
              En az 8 karakter
            </li>
            <li :class="{ gecirli: sifirlaSifreAnaliz.buyukHarf }">
              <span class="durum-ikon">{{ sifirlaSifreAnaliz.buyukHarf ? '✓' : '○' }}</span>
              En az bir büyük harf (A-Z)
            </li>
            <li :class="{ gecirli: sifirlaSifreAnaliz.kucukHarf }">
              <span class="durum-ikon">{{ sifirlaSifreAnaliz.kucukHarf ? '✓' : '○' }}</span>
              En az bir küçük harf (a-z)
            </li>
            <li :class="{ gecirli: sifirlaSifreAnaliz.rakamKuraliGecerli }">
              <span class="durum-ikon">{{ sifirlaSifreAnaliz.rakamKuraliGecerli ? '✓' : '○' }}</span>
              Tekrar eden veya sıralı rakam bulunmaması önerilir
            </li>
          </ul>
        </div>
      </div>
      <button
  id="btn-sifre-yenile"
  type="submit"
  class="btn btn-turuncu"
  :disabled="islem || !sifirlaSifreAnaliz.uzunluk || !sifirlaSifreAnaliz.buyukHarf || !sifirlaSifreAnaliz.kucukHarf"
>
        {{ islem ? 'Güncelleniyor…' : 'Şifremi Güncelle →' }}
      </button>
      <button type="button" class="btn btn-geri" @click="resetFormSifirla">
        ← Giriş Yap
      </button>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'

const emit = defineEmits(['success', 'error', 'close'])

const form = ref({ email: '', kod: '', yeniSifre: '', kodAsamasi: false })
const islem = ref(false)
const gozGoster = ref(false)
const geriSayim = ref(0)
let timer: ReturnType<typeof setInterval> | null = null

function timerBaslat() {
  geriSayim.value = 60
  if (timer) clearInterval(timer)
  timer = setInterval(() => {
    if (geriSayim.value > 0) {
      geriSayim.value--
    } else {
      if (timer) clearInterval(timer)
    }
  }, 1000)
}

onUnmounted(() => {
  if (timer) clearInterval(timer)
})

function rakamKuralKontrol(s: string): boolean {
  if (s.length === 0) return false
  // 1. Yan yana tekrar eden rakam var mı? (örn: 11, 99)
  if (/(\d)\1/.test(s)) return false
  // 2. Ardışık/sıralı 3 rakam var mı? (örn: 123, 321)
  for (let i = 0; i < s.length - 2; i++) {
    const c1 = s.charCodeAt(i)
    const c2 = s.charCodeAt(i + 1)
    const c3 = s.charCodeAt(i + 2)
    if (c1 >= 48 && c1 <= 57 && c2 >= 48 && c2 <= 57 && c3 >= 48 && c3 <= 57) {
      if ((c2 === c1 + 1 && c3 === c2 + 1) || (c2 === c1 - 1 && c3 === c2 - 1)) {
        return false
      }
    }
  }
  return true
}

const sifirlaSifreAnaliz = computed(() => {
  const s = form.value.yeniSifre || ''
  const uzunluk = s.length >= 8
  const buyukHarf = /[A-Z]/.test(s)
  const kucukHarf = /[a-z]/.test(s)
  const rakamKuraliGecerli = rakamKuralKontrol(s)
  return {
    uzunluk,
    buyukHarf,
    kucukHarf,
    rakamKuraliGecerli,
    toplam: (uzunluk ? 1 : 0) + (buyukHarf ? 1 : 0) + (kucukHarf ? 1 : 0) + (rakamKuraliGecerli ? 1 : 0)
  }
})

function hataMesajiniAl(e: unknown): string {
  if (e && typeof e === 'object' && 'data' in e) {
    const data = (e as { data?: { message?: string } }).data
    if (data?.message) return data.message
  }
  if (e instanceof Error) return e.message
  return 'Beklenmedik bir hata oluştu.'
}

async function sifreSifirlaBaslat() {
  islem.value = true
  emit('error', '')
  try {
    const veri = await $fetch<{ message: string }>('/api/sifre-baslat', {
      method : 'POST',
      body   : { email: form.value.email },
    })
    emit('success', veri.message)
    form.value.kodAsamasi = true
    form.value.kod = ''
    form.value.yeniSifre = ''
    timerBaslat() // İlk gönderimde de geri sayımı başlat
  } catch (e) {
    emit('error', hataMesajiniAl(e))
  } finally {
    islem.value = false
  }
}

async function sifreYenile() {
  islem.value = true
  emit('error', '')
  try {
    const veri = await $fetch<{ message: string }>('/api/sifre-yenile', {
      method : 'POST',
      body   : {
        email     : form.value.email,
        kod       : form.value.kod,
        yeniSifre : form.value.yeniSifre,
      },
    })
    emit('success', veri.message)
    resetFormSifirla()
    setTimeout(() => {
      emit('close')
    }, 2000)
  } catch (e) {
    emit('error', hataMesajiniAl(e))
  } finally {
    islem.value = false
  }
}

async function kodYenidenGonder() {
  islem.value = true
  emit('error', '')
  try {
    const veri = await $fetch<{ message: string }>('/api/sifre-baslat', {
      method : 'POST',
      body   : { email: form.value.email },
    })
    emit('success', veri.message)
    timerBaslat()
  } catch (e) {
    emit('error', hataMesajiniAl(e))
  } finally {
    islem.value = false
  }
}

function resetFormSifirla() {
  form.value = { email: '', kod: '', yeniSifre: '', kodAsamasi: false }
  if (timer) {
    clearInterval(timer)
    timer = null
  }
  geriSayim.value = 0
  emit('close')
}
</script>

