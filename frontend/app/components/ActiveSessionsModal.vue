<template>
  <ClientOnly>
    <Teleport to="body">
      <Transition name="modal-fade">
        <div v-if="modelValue" class="modal-overlay" @click.self="kapat">
          <div class="modal-icerik" role="dialog" aria-labelledby="modal-oturumlar-baslik" aria-modal="true">
            <!-- Header -->
            <div class="modal-baslik-alan">
              <div class="baslik-sol">
                <span class="baslik-ikon">📱</span>
                <div>
                  <h3 id="modal-oturumlar-baslik" class="modal-baslik">Aktif Oturumlar</h3>
                  <small class="modal-alt">Hesabınızın açık olduğu cihazlar</small>
                </div>
              </div>
              <button type="button" class="modal-kapat-btn" @click="kapat" title="Kapat">✕</button>
            </div>

            <!-- Error/Status Message -->
            <div v-if="hataMesaji" class="oturum-hata">
              {{ hataMesaji }}
            </div>

            <!-- Loading Spinner -->
            <div v-if="yukleniyor" class="oturum-yukleniyor">
              <div class="spinner-kucuk"></div>
              <span>Oturum bilgileri yükleniyor…</span>
            </div>

            <!-- Sessions List -->
            <div v-else class="modal-govde">
              <div v-if="oturumlar.length === 0" class="bos-oturum">
                Aktif oturum bulunamadı.
              </div>

              <div
                v-for="o in oturumlar"
                :key="o.token"
                class="oturum-kart"
                :class="{ 'bu-cihaz-kart': o.buCihazMi }"
              >
                <div class="oturum-simge">
                  {{ cihazSimgesi(o.userAgent) }}
                </div>
                
                <div class="oturum-detay">
                  <div class="oturum-ust">
                    <span class="cihaz-adi">{{ cihazAdi(o.userAgent) }}</span>
                    <span v-if="o.buCihazMi" class="badge-bu-cihaz">Bu Cihaz</span>
                  </div>
                  <div class="oturum-bilgi-satir">
                    <span class="ip-etiket">🌐 IP: {{ o.ipAdresi }}</span>
                    <span class="tarih-etiket">🕒 {{ tarihFormat(o.olusturulma) }}</span>
                  </div>
                </div>

                <button
                  type="button"
                  class="btn-oturum-kapat"
                  :disabled="islemToken === o.token"
                  @click="tekOturumKapat(o.token)"
                  title="Bu Oturumu Kapat"
                >
                  {{ islemToken === o.token ? '…' : 'Kapat' }}
                </button>
              </div>
            </div>

            <!-- Footer Action -->
            <div class="modal-alt-alan">
              <button
                type="button"
                class="btn btn-tum-kapat"
                :disabled="tumKapatIslem || yukleniyor || oturumlar.length === 0"
                @click="tumOturumlariKapat"
              >
                🚪 {{ tumKapatIslem ? 'Kapatılıyor…' : 'Tüm Cihazlardan Çıkış Yap' }}
              </button>
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

const emit = defineEmits(['update:modelValue', 'allRevoked', 'sessionRevoked'])

interface OturumItem {
  token: string
  ipAdresi: string
  userAgent: string
  olusturulma: string
  sonKullanma: string
  buCihazMi: boolean
}

const oturumlar = ref<OturumItem[]>([])
const yukleniyor = ref(false)
const tumKapatIslem = ref(false)
const islemToken = ref<string | null>(null)
const hataMesaji = ref('')

function kapat() {
  emit('update:modelValue', false)
}

watch(
  () => props.modelValue,
  (yeniVal) => {
    if (yeniVal) {
      oturumYukle()
    }
  }
)

async function oturumYukle() {
  yukleniyor.value = true
  hataMesaji.value = ''
  try {
    const veri = await $fetch<{ success: boolean; oturumlar: OturumItem[] }>('/api/oturumlar')
    oturumlar.value = veri.oturumlar || []
  } catch (err: unknown) {
    hataMesaji.value = 'Oturum bilgileri alınamadı.'
  } finally {
    yukleniyor.value = false
  }
}

async function tekOturumKapat(token: string) {
  islemToken.value = token
  hataMesaji.value = ''
  try {
    await $fetch('/api/oturum-kapat', {
      method: 'POST',
      body: { token },
    })
    oturumlar.value = oturumlar.value.filter((o) => o.token !== token)
    emit('sessionRevoked')
  } catch (err: unknown) {
    hataMesaji.value = 'Oturum kapatılamadı.'
  } finally {
    islemToken.value = null
  }
}

async function tumOturumlariKapat() {
  if (!confirm('Tüm cihazlardaki oturumlarınız sonlandırılacak. Devam etmek istiyor musunuz?')) return

  tumKapatIslem.value = true
  hataMesaji.value = ''
  try {
    await $fetch('/api/tum-oturumlari-kapat', { method: 'POST' })
    oturumlar.value = []
    kapat()
    emit('allRevoked')
  } catch (err: unknown) {
    hataMesaji.value = 'Tüm oturumlar kapatılamadı.'
  } finally {
    tumKapatIslem.value = false
  }
}

function cihazSimgesi(ua: string): string {
  const s = ua.toLowerCase()
  if (s.includes('mobile') || s.includes('android') || s.includes('iphone')) return '📱'
  if (s.includes('mac')) return '💻'
  if (s.includes('windows')) return '🖥️'
  if (s.includes('postman')) return '🚀'
  return '🌐'
}

function cihazAdi(ua: string): string {
  const s = ua.toLowerCase()
  if (s.includes('postman')) return 'Postman API Client'
  let browser = 'Tarayıcı'
  if (s.includes('chrome')) browser = 'Chrome'
  else if (s.includes('firefox')) browser = 'Firefox'
  else if (s.includes('safari')) browser = 'Safari'
  else if (s.includes('edge')) browser = 'Edge'

  let os = 'Bilinmeyen Cihaz'
  if (s.includes('windows')) os = 'Windows'
  else if (s.includes('mac')) os = 'macOS'
  else if (s.includes('android')) os = 'Android'
  else if (s.includes('iphone')) os = 'iOS'
  else if (s.includes('linux')) os = 'Linux'

  return `${browser} (${os})`
}

function tarihFormat(tStr: string): string {
  try {
    const d = new Date(tStr)
    return d.toLocaleDateString('tr-TR', {
      day: '2-digit',
      month: 'short',
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
  background: rgba(41, 48, 66, 0.35);
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
  max-height: 85vh;
  background: #ffffff;
  border: 1px solid #e5e7f0;
  border-radius: 18px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 25px 50px -12px rgba(77, 86, 140, 0.16), 0 0 0 1px rgba(142, 137, 196, 0.2);
  color: #e5e7eb;
}

.modal-baslik-alan {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 16px;
  border-bottom: 1px solid #e5e7f0;
}

.baslik-sol {
  display: flex;
  align-items: center;
  gap: 12px;
}

.baslik-ikon {
  font-size: 1.8rem;
}

.modal-baslik {
  font-size: 1.2rem;
  font-weight: 700;
  color: #293042;
}

.modal-alt {
  color: #737d90;
  font-size: 0.78rem;
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
  color: #8572b7;
  background: #efecf7;
}

.oturum-hata {
  background: rgba(180, 95, 123, 0.15);
  border: 1px solid rgba(180, 95, 123, 0.3);
  color: #b45f7b;
  font-size: 0.84rem;
  padding: 10px 14px;
  border-radius: 8px;
  margin-top: 12px;
}

.oturum-yukleniyor {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 32px;
  color: #737d90;
  font-size: 0.88rem;
}

.spinner-kucuk {
  width: 20px; height: 20px;
  border: 2px solid #e5e7f0;
  border-top-color: #8e89c4;
  border-radius: 50%;
  animation: don 0.7s linear infinite;
}

@keyframes don { to { transform: rotate(360deg); } }

.modal-govde {
  overflow-y: auto;
  padding: 16px 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 50vh;
}

.bos-oturum {
  text-align: center;
  color: #737d90;
  padding: 24px;
  font-size: 0.88rem;
}

.oturum-kart {
  display: flex;
  align-items: center;
  gap: 14px;
  background: #f6f4fb;
  border: 1px solid #e5e7f0;
  border-radius: 12px;
  padding: 14px 16px;
  transition: border-color 0.2s;
}

.bu-cihaz-kart {
  background: rgba(142, 137, 196, 0.08);
  border-color: rgba(142, 137, 196, 0.3);
}

.oturum-simge {
  font-size: 1.6rem;
  flex-shrink: 0;
}

.oturum-detay {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.oturum-ust {
  display: flex;
  align-items: center;
  gap: 8px;
}

.cihaz-adi {
  font-weight: 600;
  font-size: 0.9rem;
  color: #293042;
}

.badge-bu-cihaz {
  background: rgba(94, 169, 150, 0.2);
  color: #4f9583;
  border: 1px solid rgba(94, 169, 150, 0.3);
  font-size: 0.7rem;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 6px;
}

.oturum-bilgi-satir {
  display: flex;
  gap: 12px;
  font-size: 0.76rem;
  color: #737d90;
}

.btn-oturum-kapat {
  background: rgba(180, 95, 123, 0.12);
  border: 1px solid rgba(180, 95, 123, 0.25);
  color: #c26a86;
  font-size: 0.78rem;
  font-weight: 600;
  padding: 6px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.btn-oturum-kapat:hover {
  background: rgba(180, 95, 123, 0.25);
}

.modal-alt-alan {
  padding-top: 16px;
  border-top: 1px solid #e5e7f0;
}

.btn-tum-kapat {
  background: linear-gradient(135deg, #d48aa2, #b45f7b);
  color: #fff;
  font-weight: 700;
  width: 100%;
  padding: 12px;
  border-radius: 10px;
  border: none;
  cursor: pointer;
  box-shadow: 0 4px 20px rgba(180, 95, 123, 0.3);
  transition: all 0.2s;
}

.btn-tum-kapat:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 25px rgba(180, 95, 123, 0.45);
}

.btn-tum-kapat:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Transitions */
.modal-fade-enter-active, .modal-fade-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.modal-fade-enter-from, .modal-fade-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>
