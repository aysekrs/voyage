
<template>
  <ClientOnly>
    <Teleport to="body">
      <Transition name="modal-fade">
        <div v-if="modelValue" class="modal-overlay" @click.self="kapat">
          <div class="modal-icerik" role="dialog" aria-labelledby="modal-profil-baslik" aria-modal="true">
            <!-- Header -->
            <div class="modal-baslik-alan">
              <div class="baslik-sol">
                <span class="baslik-ikon">⚙️</span>
                <div>
                  <h3 id="modal-profil-baslik" class="modal-baslik">Profil & Hesap Ayarları</h3>
                  <small class="modal-alt">Hesap bilgilerinizi ve şifrenizi yönetin</small>
                </div>
              </div>
              <button type="button" class="modal-kapat-btn" @click="kapat" title="Kapat">✕</button>
            </div>

            <!-- Tab Navigation -->
            <div class="sekme-nav">
              <button
                type="button"
                class="sekme-btn"
                :class="{ aktif: aktifSekme === 'bilgiler' }"
                @click="aktifSekme = 'bilgiler'"
              >
                👤 Bilgiler
              </button>
              <button
                type="button"
                class="sekme-btn"
                :class="{ aktif: aktifSekme === 'sifre' }"
                @click="aktifSekme = 'sifre'"
              >
                🔑 Şifre Değiştir
              </button>
              <button
                type="button"
                class="sekme-btn"
                :class="{ aktif: aktifSekme === 'email' }"
                @click="aktifSekme = 'email'"
              >
                📧 E-posta Değiştir
              </button>
              <button
                type="button"
                class="sekme-btn sekme-tehlikeli"
                :class="{ aktif: aktifSekme === 'hesapSil' }"
                @click="aktifSekme = 'hesapSil'"
              >
                🗑️ Hesabı Sil
              </button>
            </div>

            <!-- Global Status / Error Message -->
            <div v-if="mesaj" class="profil-mesaj" :class="mesajTuru">
              {{ mesaj }}
            </div>

            <!-- Loading Spinner -->
            <div v-if="yukleniyor" class="profil-yukleniyor">
              <div class="spinner-kucuk"></div>
              <span>Profil yükleniyor…</span>
            </div>

            <!-- TAB 1: Bilgiler -->
            <div v-else-if="aktifSekme === 'bilgiler'" class="sekme-icerik">
              <div class="bilgi-grup">
                <label>Kullanıcı Adı</label>
                <div class="bilgi-deger">@{{ profil?.kullanici }}</div>
              </div>
              <div class="bilgi-grup">
                <label>E-posta Adresi</label>
                <div class="bilgi-deger">{{ profil?.email }}</div>
              </div>
              <div class="bilgi-grup">
                <label>Kayıt Tarihi</label>
                <div class="bilgi-deger">{{ tarihFormat(profil?.olusturulma) }}</div>
              </div>
              <div class="bilgi-grup">
                <label>KVKK Onay Durumu</label>
                <div class="bilgi-deger kvkk-deger">
                  <span class="kvkk-rozet">
                    {{ profil?.kvkkOnay ? '✓ Onaylandı' : 'Onay bilgisi mevcut değil' }}
                  </span>
                  <small v-if="profil?.kvkkOnayTarihi">
                    ({{ tarihFormat(profil?.kvkkOnayTarihi) }})
                  </small>
                </div>
              </div>
            </div>

            <!-- TAB 2: Şifre Değiştir -->
            <form v-else-if="aktifSekme === 'sifre'" class="sekme-icerik" @submit.prevent="sifreDegistir">
              <div class="girdi-grup">
                <label for="prof-mevcut-sifre">Mevcut Şifreniz</label>
                <input
                  id="prof-mevcut-sifre"
                  v-model="mevcutSifre"
                  type="password"
                  placeholder="Mevcut şifrenizi girin"
                  required
                />
              </div>

              <div class="girdi-grup">
                <label for="prof-yeni-sifre">Yeni Şifre</label>
                <input
                  id="prof-yeni-sifre"
                  v-model="yeniSifre"
                  type="password"
                  placeholder="En az 8 karakter (Büyük/küçük harf)"
                  required
                />
              </div>

              <button type="submit" class="btn btn-birincil" :disabled="islem">
                {{ islem ? 'Güncelleniyor…' : 'Şifreyi Güncelle' }}
              </button>
            </form>

            <!-- TAB 3: E-posta Değiştir -->
            <div v-else-if="aktifSekme === 'email'" class="sekme-icerik">
              <!-- Adım 1: Şifre ve Yeni E-posta İsteme -->
              <form v-if="emailAdim === 1" @submit.prevent="emailDegisiklikBaslat">
                <div class="girdi-grup">
                  <label for="prof-email-sifre">Mevcut Şifreniz</label>
                  <input
                    id="prof-email-sifre"
                    v-model="mevcutSifre"
                    type="password"
                    placeholder="Mevcut şifrenizi doğrulayın"
                    required
                  />
                </div>

                <div class="girdi-grup">
                  <label for="prof-yeni-email">Yeni E-posta Adresi</label>
                  <input
                    id="prof-yeni-email"
                    v-model="yeniEmail"
                    type="email"
                    placeholder="yeni@ornek.com"
                    required
                  />
                </div>

                <button type="submit" class="btn btn-birincil" :disabled="islem">
                  {{ islem ? 'Kod Gönderiliyor…' : 'Doğrulama Kodu Gönder' }}
                </button>
              </form>

              <!-- Adım 2: OTP Kod Onaylama -->
              <form v-else @submit.prevent="emailKodDogrula">
                <div class="bilgi-kutu">
                  📩 <strong>{{ yeniEmail }}</strong> adresine 6 haneli doğrulama kodu gönderildi.
                </div>

                <div class="girdi-grup">
                  <label for="prof-email-kod">6 Haneli Doğrulama Kodu</label>
                  <input
                    id="prof-email-kod"
                    v-model="emailKod"
                    type="text"
                    maxlength="6"
                    placeholder="123456"
                    required
                  />
                </div>

                <div class="buton-cifti">
                  <button type="button" class="btn btn-ikincil" @click="emailAdim = 1">Geri</button>
                  <button type="submit" class="btn btn-birincil" :disabled="islem">
                    {{ islem ? 'Onaylanıyor…' : 'E-postayı Onayla' }}
                  </button>
                </div>
              </form>
            </div>

            <!-- TAB 4: Hesabı Sil -->
            <div v-else-if="aktifSekme === 'hesapSil'" class="sekme-icerik tehlikeli-icerik">
              <div class="kilitli-uyari">
                <strong>⚠️ HESAP SİLME İŞLEMİ GERİ ALINAMAZ</strong>
                <p>Hesabınızı ve evcil hayvanınızı (Level, Coin, Aksesuarlar) kalıcı olarak silmek üzeresiniz. Lütfen devam etmek için mevcut şifrenizi girin.</p>
              </div>

              <form @submit.prevent="hesapSil">
                <div class="girdi-grup">
                  <label for="prof-sil-sifre">Mevcut Şifreniz</label>
                  <input
                    id="prof-sil-sifre"
                    v-model="mevcutSifre"
                    type="password"
                    placeholder="Mevcut şifrenizi onaylayın"
                    required
                  />
                </div>

                <button type="submit" class="btn btn-tehlikeli" :disabled="islem">
                  {{ islem ? 'Siliniyor…' : '🗑️ Hesabımı ve Tüm Verilerimi Kalıcı Olarak Sil' }}
                </button>
              </form>
            </div>

            <!-- Footer -->
            <div class="modal-alt-alan">
              <button type="button" class="btn btn-kapat-birincil" @click="kapat">Kapat</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </ClientOnly>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits(['update:modelValue', 'profileUpdated'])

interface ProfilData {
  kullanici: string
  email: string
  olusturulma: string
  kvkkOnay: boolean
  kvkkOnayTarihi: string | null
}

const aktifSekme = ref<'bilgiler' | 'sifre' | 'email' | 'hesapSil'>('bilgiler')
const profil = ref<ProfilData | null>(null)
const yukleniyor = ref(false)
const islem = ref(false)
const mesaj = ref('')
const mesajTuru = ref<'hata' | 'basari'>('basari')

// Şifre Değiştir Formu
const mevcutSifre = ref('')
const yeniSifre = ref('')

// E-posta Değiştir Formu
const yeniEmail = ref('')
const emailKod = ref('')
const emailAdim = ref<1 | 2>(1)

function kapat() {
  emit('update:modelValue', false)
}

watch(
  () => props.modelValue,
  (yeniVal) => {
    if (yeniVal) {
      profilYukle()
      formSifirla()
    }
  }
)

function formSifirla() {
  mevcutSifre.value = ''
  yeniSifre.value = ''
  yeniEmail.value = ''
  emailKod.value = ''
  emailAdim.value = 1
  mesaj.value = ''
}



async function profilYukle() {
  yukleniyor.value = true
  mesaj.value = ''

  try {
    const res = await $fetch<{
      kullanici: string
      email: string
      olusturulma: string
      kvkkOnay: boolean | null
      kvkkOnayTarihi: string | null
    }>('/api/ben')

    profil.value = {
      kullanici: res.email.split('@')[0] || '',
      email: res.email,
      olusturulma: res.olusturulma,
      kvkkOnay: res.kvkkOnay ?? false,
      kvkkOnayTarihi: res.kvkkOnayTarihi
    }
  } catch (err: unknown) {
    profil.value = null
    mesajGoster('Profil bilgileri alınamadı.', 'hata')
  } finally {
    yukleniyor.value = false
  }
}



async function sifreDegistir() {
  islem.value = true
  mesaj.value = ''
  try {
    const res = await $fetch<{ success: boolean; message: string }>('/api/profil/sifre-degistir', {
      method: 'POST',
      body: {
        mevcutSifre: mevcutSifre.value,
        yeniSifre: yeniSifre.value,
      },
    })
    mesajGoster(res.message, 'basari')
    mevcutSifre.value = ''
    yeniSifre.value = ''
  } catch (err: unknown) {
    const msg = (err as { data?: { message?: string } })?.data?.message || 'Şifre değiştirilemedi.'
    mesajGoster(msg, 'hata')
  } finally {
    islem.value = false
  }
}

async function emailDegisiklikBaslat() {
  islem.value = true
  mesaj.value = ''
  try {
    const res = await $fetch<{ success: boolean; message: string }>('/api/profil/email-degistir', {
      method: 'POST',
      body: {
        mevcutSifre: mevcutSifre.value,
        yeniEmail: yeniEmail.value,
      },
    })
    mesajGoster(res.message, 'basari')
    emailAdim.value = 2
  } catch (err: unknown) {
    const msg = (err as { data?: { message?: string } })?.data?.message || 'E-posta değiştirme başlatılamadı.'
    mesajGoster(msg, 'hata')
  } finally {
    islem.value = false
  }
}

async function emailKodDogrula() {
  islem.value = true
  mesaj.value = ''
  try {
    const res = await $fetch<{ success: boolean; message: string }>('/api/profil/email-dogrula', {
      method: 'POST',
      body: {
        yeniEmail: yeniEmail.value,
        kod: emailKod.value,
      },
    })
    mesajGoster(res.message, 'basari')
    if (profil.value) profil.value.email = yeniEmail.value
    emailAdim.value = 1
    mevcutSifre.value = ''
    yeniEmail.value = ''
    emailKod.value = ''
    emit('profileUpdated')
  } catch (err: unknown) {
    const msg = (err as { data?: { message?: string } })?.data?.message || 'Doğrulama başarısız.'
    mesajGoster(msg, 'hata')
  } finally {
    islem.value = false
  }
}

async function hesapSil() {
  if (!confirm('Hesabınızı ve verilerinizi kalıcı olarak silmek istediğinizden emin misiniz? Bu işlem geri alınamaz!')) {
    return
  }

  islem.value = true
  mesaj.value = ''
  try {
    const res = await $fetch<{ success: boolean; message: string }>('/api/profil/hesap-sil', {
      method: 'DELETE',
      body: { mevcutSifre: mevcutSifre.value }
    })
    alert(res.message)
    window.location.href = '/'
  } catch (err: unknown) {
    const msg = (err as { data?: { message?: string } })?.data?.message || 'Hesap silme başarısız.'
    mesajGoster(msg, 'hata')
  } finally {
    islem.value = false
  }
}

function mesajGoster(m: string, tur: 'hata' | 'basari') {
  mesaj.value = m
  mesajTuru.value = tur
}

function tarihFormat(tStr?: string | null): string {
  if (!tStr) return '-'
  try {
    const d = new Date(tStr)
    return d.toLocaleDateString('tr-TR', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return tStr
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0; left: 0;
  width: 100vw; height: 100vh;
  background: rgba(10, 14, 26, 0.82);
  backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 20px;
}

.modal-icerik {
  width: 100%;
  max-width: 520px;
  background: #111827;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 18px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.75), 0 0 0 1px rgba(99, 102, 241, 0.2);
  color: #e5e7eb;
}

.modal-baslik-alan {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.baslik-sol {
  display: flex;
  align-items: center;
  gap: 12px;
}

.baslik-ikon { font-size: 1.8rem; }
.modal-baslik { font-size: 1.2rem; font-weight: 700; color: #fff; }
.modal-alt { color: rgba(255, 255, 255, 0.45); font-size: 0.78rem; }

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
.modal-kapat-btn:hover { color: #fff; background: rgba(255, 255, 255, 0.1); }

.sekme-nav {
  display: flex;
  gap: 6px;
  margin-top: 14px;
  background: rgba(255, 255, 255, 0.04);
  padding: 4px;
  border-radius: 10px;
}

.sekme-btn {
  flex: 1;
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.5);
  font-size: 0.8rem;
  font-weight: 600;
  padding: 8px 4px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.sekme-btn.aktif {
  background: rgba(99, 102, 241, 0.25);
  color: #fff;
  border: 1px solid rgba(99, 102, 241, 0.4);
}

.profil-mesaj {
  font-size: 0.82rem;
  padding: 10px 14px;
  border-radius: 8px;
  margin-top: 12px;
}
.profil-mesaj.basari {
  background: rgba(16, 185, 129, 0.15);
  border: 1px solid rgba(16, 185, 129, 0.3);
  color: #34d399;
}
.profil-mesaj.hata {
  background: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #fca5a5;
}

.profil-yukleniyor {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 32px;
  color: rgba(255, 255, 255, 0.5);
  font-size: 0.88rem;
}

.spinner-kucuk {
  width: 20px; height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.1);
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: don 0.7s linear infinite;
}
@keyframes don { to { transform: rotate(360deg); } }

.sekme-icerik {
  padding: 16px 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.bilgi-grup {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.bilgi-grup label {
  font-size: 0.76rem;
  color: rgba(255, 255, 255, 0.45);
  font-weight: 600;
}
.bilgi-deger {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 0.9rem;
  color: #fff;
}

.kvkk-deger { display: flex; align-items: center; gap: 8px; }
.kvkk-rozet { color: #34d399; font-weight: 700; font-size: 0.82rem; }

.girdi-grup {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.girdi-grup label {
  font-size: 0.78rem;
  color: rgba(255, 255, 255, 0.6);
  font-weight: 600;
}
.girdi-grup input {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  padding: 10px 14px;
  color: #fff;
  font-size: 0.9rem;
  outline: none;
  transition: border-color 0.2s;
}
.girdi-grup input:focus {
  border-color: #6366f1;
}

.bilgi-kutu {
  background: rgba(99, 102, 241, 0.12);
  border: 1px solid rgba(99, 102, 241, 0.25);
  color: #a5b4fc;
  font-size: 0.82rem;
  padding: 10px 14px;
  border-radius: 8px;
}

.buton-cifti {
  display: flex;
  gap: 10px;
}

.btn-ikincil {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  border: none;
  padding: 11px;
  border-radius: 10px;
  cursor: pointer;
}

.btn-birincil {
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  color: #fff;
  font-weight: 700;
  padding: 11px;
  border-radius: 10px;
  border: none;
  cursor: pointer;
  flex: 1;
}

.modal-alt-alan {
  padding-top: 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}
.btn-kapat-birincil {
  background: rgba(255, 255, 255, 0.08);
  color: #e5e7eb;
  font-weight: 600;
  width: 100%;
  padding: 10px;
  border-radius: 10px;
  border: none;
  cursor: pointer;
}

.modal-fade-enter-active, .modal-fade-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.modal-fade-enter-from, .modal-fade-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>
