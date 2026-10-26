<template>
  <form id="form-giris" class="voyage-login" @submit.prevent="girisYap">
    <div class="alan">
      <label for="giris-email">E-POSTA ADRESİ</label>
      <div class="input-wrap">
        <svg class="field-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/></svg>
        <input id="giris-email" v-model="form.email" type="email" placeholder="ornek@email.com" autocomplete="email" required />
      </div>
    </div>

    <div class="alan">
      <label for="giris-sifre">ŞİFRE</label>
      <div class="input-wrap">
        <svg class="field-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg>
        <input id="giris-sifre" v-model="form.sifre" :type="gozGoster ? 'text' : 'password'" placeholder="••••••••" autocomplete="current-password" required />
        <button type="button" class="goz-btn" @click="gozGoster = !gozGoster" :title="gozGoster ? 'Şifreyi Gizle' : 'Şifreyi Göster'" :aria-label="gozGoster ? 'Şifreyi gizle' : 'Şifreyi göster'">
          <svg v-if="gozGoster" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg>
        </button>
      </div>
    </div>

    <div class="options-row">
      <label class="hatirla-alan"><input id="giris-hatirla" v-model="form.beniHatirla" type="checkbox" /><span>Beni hatırla</span></label>
      <button type="button" class="forgot-link" @click="$emit('forgotPassword')">Şifremi Unuttum?</button>
    </div>

    <div v-if="kilitli" class="kilitli-kutu" role="alert">
      <span class="kilit-ikon">🔒</span>
      <div><strong>Hesabınız kilitlendi</strong><p>5 kez hatalı şifre girildiği için girişler geçici olarak durduruldu.</p><span class="sayac-metin">Kalan süre: <strong>{{ kalanSaniyeFormatli }}</strong></span></div>
    </div>

    <button id="btn-giris" type="submit" class="voyage-submit" :disabled="islem || kilitli">
      {{ kilitli ? `Hesabınız Kilitli (${kalanSaniyeFormatli})` : (islem ? 'Giriş yapılıyor…' : 'Voyage’a Devam Et') }}
      <span v-if="!islem && !kilitli" aria-hidden="true">→</span>
    </button>
    <div class="footer-note"><span class="compass" aria-hidden="true">✦</span> Bir sonraki yolculuğun burada başlıyor.</div>
  </form>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

const emit = defineEmits(['success', 'error', 'loginSuccess', 'forgotPassword', 'hataliGiris'])
const form = ref({ email: '', sifre: '', beniHatirla: false })
onMounted(() => {
  const kayitliEmail = localStorage.getItem('voyage_hatirlanan_email')
  if (kayitliEmail) {
    form.value.email = kayitliEmail
    form.value.beniHatirla = true
  }
})
const islem = ref(false)
const gozGoster = ref(false)
const hataliGirisSayaci = ref(0)
const kilitli = ref(false)
const kalanSaniye = ref(0)
let timer: ReturnType<typeof setInterval> | null = null

const kalanSaniyeFormatli = computed(() => {
  const dk = Math.floor(kalanSaniye.value / 60)
  const sn = kalanSaniye.value % 60
  return `${dk.toString().padStart(2, '0')}:${sn.toString().padStart(2, '0')}`
})
onUnmounted(() => kilitTimerTemizle())
function kilitTimerTemizle() {
  if (timer) { clearInterval(timer); timer = null }
}
function kilitBaslat(dakika: number) {
  kilitli.value = true
  kalanSaniye.value = dakika * 60
  kilitTimerTemizle()
  timer = setInterval(() => {
    if (kalanSaniye.value > 0) kalanSaniye.value--
    else { kilitli.value = false; kilitTimerTemizle() }
  }, 1000)
}
function hataMesajiniAl(e: unknown): string {
  if (e && typeof e === 'object' && 'data' in e) {
    const data = (e as { data?: { message?: string } }).data
    if (data?.message) return data.message
  }
  if (e instanceof Error) return e.message
  return 'Beklenmedik bir hata oluştu.'
}
async function girisYap() {
  if (kilitli.value) return
  islem.value = true
  emit('error', '')
  try {
    const veri = await $fetch<{ kullanici: string }>('/api/giris', { method: 'POST', body: form.value })
    hataliGirisSayaci.value = 0
    kilitli.value = false
    kilitTimerTemizle()
    if (form.value.beniHatirla) localStorage.setItem('voyage_hatirlanan_email', form.value.email.trim())
    else localStorage.removeItem('voyage_hatirlanan_email')
    form.value = { email: '', sifre: '', beniHatirla: false }
    emit('loginSuccess', veri.kullanici)
  } catch (e: unknown) {
    const statusCode = (e as { status?: number; statusCode?: number })?.status ?? (e as { status?: number; statusCode?: number })?.statusCode
    const errData = (e as { data?: { data?: { hataliGirisSayaci?: number; kilitli?: boolean; kalanDakika?: number } } })?.data?.data
    if (statusCode === 423 || errData?.kilitli) {
      kilitBaslat(errData?.kalanDakika ?? 15)
    } else if (statusCode === 401) {
      if (typeof errData?.hataliGirisSayaci === 'number') hataliGirisSayaci.value = errData.hataliGirisSayaci
      else hataliGirisSayaci.value++
      if (hataliGirisSayaci.value >= 5) kilitBaslat(15)
      emit('hataliGiris', hataliGirisSayaci.value)
    }
    emit('error', hataMesajiniAl(e))
  } finally {
    islem.value = false
  }
}
</script>

<style scoped>
.voyage-login{display:flex;flex-direction:column;gap:21px;width:100%;color:#14213e;font-family:inherit}
.alan{display:flex;flex-direction:column;gap:9px}
.alan>label{font-size:12px;letter-spacing:2px;font-weight:800;color:#455875}
.input-wrap{position:relative;display:flex;align-items:center}
.input-wrap input{width:100%;min-width:0;box-sizing:border-box;height:55px;border:1px solid #ccd6e7;border-radius:13px;background:rgba(255,255,255,.94);padding:0 49px 0 47px;color:#162747;font:inherit;font-size:15px;outline:none;transition:border-color .2s,box-shadow .2s}
.input-wrap input:focus{border-color:#4869ed;box-shadow:0 0 0 4px rgba(76,98,238,.12)}
.input-wrap input::placeholder{color:#97a5bb}
.field-icon{position:absolute;left:15px;width:20px;height:20px;color:#637595;pointer-events:none}
.goz-btn{position:absolute;right:8px;display:grid;place-items:center;width:38px;height:38px;padding:8px;border:0;background:transparent;color:#7b8aa3;cursor:pointer;border-radius:9px}
.goz-btn:hover{background:#eef2ff;color:#3d52c8}.goz-btn svg{width:21px;height:21px}
.options-row{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-top:-2px}
.hatirla-alan{display:inline-flex;align-items:center;gap:9px;font-size:13px;font-weight:600;color:#465675;cursor:pointer}
.hatirla-alan input{width:17px;height:17px;margin:0;accent-color:#4657e9;cursor:pointer}
.forgot-link{border:0;background:none;padding:5px 0;color:#4756e8;font:inherit;font-size:13px;font-weight:750;cursor:pointer}
.forgot-link:hover{text-decoration:underline}
.voyage-submit{width:100%;min-height:58px;display:flex;align-items:center;justify-content:center;gap:12px;padding:13px 18px;border:0;border-radius:13px;background:linear-gradient(105deg,#2353a4 0%,#3c55dc 55%,#7356f2 100%);color:#fff;font:inherit;font-size:16px;font-weight:800;cursor:pointer;box-shadow:0 12px 24px rgba(51,72,191,.2);transition:transform .2s,box-shadow .2s}
.voyage-submit:hover:not(:disabled){transform:translateY(-2px);box-shadow:0 15px 30px rgba(51,72,191,.28)}
.voyage-submit:disabled{opacity:.58;cursor:not-allowed}.voyage-submit span{font-size:23px;font-weight:400}
.footer-note{text-align:center;font-size:12px;font-style:italic;color:#8997ae;padding-top:6px}
.compass{color:#4565b4;font-size:18px;margin-right:7px}
.kilitli-kutu{display:flex;align-items:flex-start;gap:12px;padding:13px 14px;border:1px solid #fecaca;border-radius:12px;background:#fff1f2;color:#9f1239;font-size:13px}
.kilitli-kutu p{margin:5px 0}.kilit-ikon{font-size:21px}.sayac-metin{display:inline-block;margin-top:5px}
@media(max-width:420px){.voyage-login{gap:18px}.forgot-link{font-size:12px}.voyage-submit{font-size:15px}}
</style>
