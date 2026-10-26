<template>
  <div>
    <!-- Kayıt Formu — Adım 1: Bilgileri gir -->
    <form v-if="!form.dogrulamaAsamasi" id="form-kayit" @submit.prevent="kayitOl" class="form">
      <div class="alan">
        <label>E-posta Adresi</label>
        <input
          id="kayit-email"
          v-model="form.email"
          type="email"
          placeholder="ornek@mail.com"
          autocomplete="email"
          required
        />
      </div>
      <div class="alan">
        <label>Şifre</label>
        <div class="sifre-alan">
          <input
            id="kayit-sifre"
            v-model="form.sifre"
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
        <div v-if="form.sifre" class="sifre-gucu">
          <div class="guc-bar-arkaplan">
            <div class="guc-bar" :class="'seviye-' + kayitSifreAnaliz.toplam" :style="{ width: (kayitSifreAnaliz.toplam / 4) * 100 + '%' }"></div>
          </div>
          <ul class="guc-liste">
            <li :class="{ gecirli: kayitSifreAnaliz.uzunluk }">
              <span class="durum-ikon">{{ kayitSifreAnaliz.uzunluk ? '✓' : '○' }}</span>
              En az 8 karakter
            </li>
            <li :class="{ gecirli: kayitSifreAnaliz.buyukHarf }">
              <span class="durum-ikon">{{ kayitSifreAnaliz.buyukHarf ? '✓' : '○' }}</span>
              En az bir büyük harf (A-Z)
            </li>
            <li :class="{ gecirli: kayitSifreAnaliz.kucukHarf }">
              <span class="durum-ikon">{{ kayitSifreAnaliz.kucukHarf ? '✓' : '○' }}</span>
              En az bir küçük harf (a-z)
            </li>
            <li :class="{ gecirli: kayitSifreAnaliz.rakamKuraliGecerli }">
              <span class="durum-ikon">{{ kayitSifreAnaliz.rakamKuraliGecerli ? '✓' : '○' }}</span>
              Tekrar eden (99) veya sıralı (123) rakam içermez
            </li>
          </ul>
        </div>
      </div>
      <div class="alan">
        <label>Şifre Tekrarı</label>
        <div class="sifre-alan">
          <input
            id="kayit-sifre-tekrar"
            v-model="form.sifreTekrar"
            :type="gozGoster ? 'text' : 'password'"
            placeholder="Şifrenizi tekrar yazın"
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
      </div>

      <!-- KVKK Onay Kutusu -->
      <div class="kvkk-alan">
        <label class="kvkk-label">
          <input
            id="kayit-kvkk-checkbox"
            v-model="form.kvkkOnay"
            type="checkbox"
            required
          />
          <span class="kvkk-metin">
            <button type="button" class="kvkk-link-btn" @click="modalAcik = true">
              KVKK Aydınlatma Metni
            </button>'ni okudum ve kabul ediyorum.
          </span>
        </label>
      </div>

      <button id="btn-kayit" type="submit" class="btn btn-birincil" :disabled="islem || !form.kvkkOnay">
        {{ islem ? 'Gönderiliyor…' : 'Hesap Oluştur →' }}
      </button>
    </form>

    <!-- Kayıt Formu — Adım 2: Email doğrulama kodu gir -->
    <form v-else id="form-dogrula" @submit.prevent="dogrulaKodu" class="form">
      <div class="dogrulama-bilgi">
        <span class="dogrulama-ikon">📧</span>
        <p>Doğrulama kodu <strong>{{ form.email }}</strong> adresine gönderildi.</p>
      </div>
      <div class="alan">
        <label>6 Haneli Doğrulama Kodu</label>
        <input
          id="dogrulama-kod"
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
      <button id="btn-dogrula" type="submit" class="btn btn-birincil" :disabled="islem">
        {{ islem ? 'Doğrulanıyor…' : 'Kodu Onayla →' }}
      </button>
      <button type="button" class="btn btn-geri" @click="kayitFormSifirla">
        ← Geri Dön
      </button>
    </form>

    <!-- KVKK Modal Penceresi -->
    <ClientOnly>
      <Teleport to="body">
        <Transition name="modal-fade">
          <div v-if="modalAcik" class="modal-overlay" @click.self="modalAcik = false">
            <div class="modal-icerik" role="dialog" aria-labelledby="modal-baslik" aria-modal="true">
              <div class="modal-baslik-alan">
                <h3 id="modal-baslik" class="modal-baslik">📋 KVKK Aydınlatma Metni</h3>
                <button type="button" class="modal-kapat-btn" @click="modalAcik = false" title="Kapat">✕</button>
              </div>
              
              <div class="modal-govde">
                <p><strong>6698 Sayılı Kişisel Verilerin Korunması Kanunu (KVKK) Bilgilendirmesi</strong></p>
                
                <p>
                  Kullanıcılarımızın kişisel verilerinin güvenliği ve gizliliği en üst düzeyde tutulmaktadır. 
                  Sistemimize kayıt olmanız ve hizmetlerimizi kullanmanız kapsamında aşağıdaki kişisel verileriniz işlenmektedir:
                </p>

                <ul>
                  <li><strong>E-posta Adresi:</strong> Hesabınızın doğrulanması, iletişime geçilmesi ve şifre sıfırlama işlemlerinin gerçekleştirilmesi amacıyla.</li>
                  <li><strong>Hash'lenmiş Şifre:</strong> Hesabınızın güvenli bir şekilde saklanması ve yetkisiz erişimlerin önlenmesi amacıyla cryptographic salt ve hash yöntemi ile hash'lenerek.</li>
                  <li><strong>IP Adresi:</strong> 5651 sayılı kanun kapsamındaki yasal yükümlülükler ile sistem ve hesap güvenliğinin sağlanması amacıyla.</li>
                  <li><strong>Giriş Zaman Damgaları (Timestamps):</strong> Şüpheli hareketlerin tespiti, yetkisiz erişim engelleme ve oturum güvenliğinin takibi amacıyla.</li>
                </ul>

                <p>
                  Kişisel verileriniz, kanuni istisnalar haricinde üçüncü şahıslarla paylaşılmamakta ve gelişmiş şifreleme yöntemleriyle güvenli veritabanımızda muhafaza edilmektedir.
                </p>
              </div>

              <div class="modal-alt-alan">
                <button type="button" class="btn btn-birincil modal-onay-btn" @click="form.kvkkOnay = true; modalAcik = false">
                  Okudum, Anladım ve Kabul Ediyorum
                </button>
              </div>
            </div>
          </div>
        </Transition>
      </Teleport>
    </ClientOnly>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'

const emit = defineEmits(['success', 'error', 'registered'])

const form = ref({ email: '', sifre: '', sifreTekrar: '', kod: '', kvkkOnay: false, dogrulamaAsamasi: false })
const islem = ref(false)
const gozGoster = ref(false)
const modalAcik = ref(false)
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
  if (/(\d)\1/.test(s)) return false
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

const kayitSifreAnaliz = computed(() => {
  const s = form.value.sifre || ''
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

async function kayitOl() {
  islem.value = true
  emit('error', '')

  if (!form.value.kvkkOnay) {
    emit('error', 'KVKK onayı zorunludur.')
    islem.value = false
    return
  }

  // Şifre tekrarı doğrulaması
  if (form.value.sifre !== form.value.sifreTekrar) {
    emit('error', 'Şifreler uyuşmuyor. Lütfen iki alana da aynı şifreyi giriniz.')
    islem.value = false
    return
  }

  try {
    const veri = await $fetch<{ message: string }>('/api/kayitol', {
      method : 'POST',
      body   : {
        email     : form.value.email,
        sifre     : form.value.sifre,
        kvkk_onay : form.value.kvkkOnay,
      },
    })
    emit('success', veri.message)
    form.value.dogrulamaAsamasi = true
    form.value.kod = ''
    timerBaslat()
  } catch (e) {
    emit('error', hataMesajiniAl(e))
  } finally {
    islem.value = false
  }
}

async function dogrulaKodu() {
  islem.value = true
  emit('error', '')
  try {
    const veri = await $fetch<{ message: string }>('/api/dogrula', {
      method : 'POST',
      body   : {
        email : form.value.email,
        kod   : form.value.kod,
      },
    })
    emit('success', veri.message)
    kayitFormSifirla()
    emit('registered')
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
    const veri = await $fetch<{ message: string }>('/api/resend-otp', {
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

function kayitFormSifirla() {
  form.value = { email: '', sifre: '', sifreTekrar: '', kod: '', kvkkOnay: false, dogrulamaAsamasi: false }
  if (timer) {
    clearInterval(timer)
    timer = null
  }
  geriSayim.value = 0
}
</script>

<style scoped>
.kvkk-alan {
  margin-top: 4px;
  margin-bottom: 4px;
}

.kvkk-label {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  cursor: pointer;
  user-select: none;
  font-size: 0.84rem;
  color: rgba(255, 255, 255, 0.7);
  line-height: 1.45;
}

.kvkk-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  margin-top: 2px;
  accent-color: #6366f1;
  cursor: pointer;
  flex-shrink: 0;
}

.kvkk-link-btn {
  background: none;
  border: none;
  color: #818cf8;
  font-size: inherit;
  font-weight: 600;
  padding: 0;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 3px;
  transition: color 0.2s;
}

.kvkk-link-btn:hover {
  color: #a5b4fc;
}

/* ─── Modal Stilleri ────────────────────────────────────────── */
.modal-overlay {
  position: fixed;
  top: 0; left: 0;
  width: 100vw; height: 100vh;
  background: rgba(10, 14, 26, 0.8);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 20px;
}

.modal-icerik {
  width: 100%;
  max-width: 520px;
  max-height: 85vh;
  background: #111827;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 16px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7), 0 0 0 1px rgba(99, 102, 241, 0.15);
  color: #e5e7eb;
}

.modal-baslik-alan {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.modal-baslik {
  font-size: 1.15rem;
  font-weight: 700;
  color: #fff;
}

.modal-kapat-btn {
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.5);
  font-size: 1.2rem;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: all 0.2s;
}

.modal-kapat-btn:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
}

.modal-govde {
  overflow-y: auto;
  padding: 16px 0;
  font-size: 0.88rem;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.8);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.modal-govde ul {
  padding-left: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.modal-govde li {
  color: rgba(255, 255, 255, 0.75);
}

.modal-govde strong {
  color: #a5b4fc;
}

.modal-alt-alan {
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.modal-onay-btn {
  margin-top: 0;
}

/* Modal Geçiş Efekti */
.modal-fade-enter-active, .modal-fade-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.modal-fade-enter-from, .modal-fade-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>
