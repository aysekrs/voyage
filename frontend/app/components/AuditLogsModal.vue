<template>
  <ClientOnly>
    <Teleport to="body">
      <Transition name="modal-fade">
        <div v-if="modelValue" class="modal-overlay" @click.self="kapat">
          <div class="modal-icerik" role="dialog" aria-labelledby="modal-loglar-baslik" aria-modal="true">
            <!-- Header -->
            <div class="modal-baslik-alan">
              <div class="baslik-sol">
                <span class="baslik-ikon">📜</span>
                <div>
                  <h3 id="modal-loglar-baslik" class="modal-baslik">Güvenlik Denetim Logları</h3>
                  <small class="modal-alt">Hesabınızla ilgili tüm güvenlik hareketleri</small>
                </div>
              </div>
              <button type="button" class="modal-kapat-btn" @click="kapat" title="Kapat">✕</button>
            </div>

            <!-- Error Status -->
            <div v-if="hataMesaji" class="log-hata">
              {{ hataMesaji }}
            </div>

            <!-- Loading Spinner -->
            <div v-if="yukleniyor" class="log-yukleniyor">
              <div class="spinner-kucuk"></div>
              <span>Güvenlik geçmişi yükleniyor…</span>
            </div>

            <!-- Logs List -->
            <div v-else class="modal-govde">
              <div v-if="loglar.length === 0" class="bos-log">
                Henüz kayıtlı güvenlik hareketi bulunamadı.
              </div>

              <div
                v-for="l in loglar"
                :key="l.id"
                class="log-kart"
              >
                <div class="log-ikon-kutusu" :class="islemSinifi(l.islemTuru)">
                  {{ islemSimgesi(l.islemTuru) }}
                </div>

                <div class="log-detay">
                  <div class="log-ust">
                    <span class="islem-baslik">{{ islemEtiketi(l.islemTuru) }}</span>
                    <span class="log-tarih">{{ tarihFormat(l.olusturulma) }}</span>
                  </div>
                  <div class="log-alt">
                    <span class="ip-etiket">🌐 {{ l.ipAdresi }}</span>
                    <span v-if="l.detay" class="detay-metin">{{ detayFormat(l.detay) }}</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="modal-alt-alan">
              <button type="button" class="btn btn-kapat-birincil" @click="kapat">
                Anladım / Kapat
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

const emit = defineEmits(['update:modelValue'])

interface AuditLogItem {
  id: number
  islemTuru: string
  ipAdresi: string
  detay: string | null
  olusturulma: string
}

const loglar = ref<AuditLogItem[]>([])
const yukleniyor = ref(false)
const hataMesaji = ref('')

function kapat() {
  emit('update:modelValue', false)
}

watch(
  () => props.modelValue,
  (yeniVal) => {
    if (yeniVal) {
      loglariYukle()
    }
  }
)

async function loglariYukle() {
  yukleniyor.value = true
  hataMesaji.value = ''
  try {
    const veri = await $fetch<{ success: boolean; loglar: AuditLogItem[] }>('/api/guvenlik-loglari')
    loglar.value = veri.loglar || []
  } catch (err: unknown) {
    hataMesaji.value = 'Güvenlik geçmişi yüklenemedi.'
  } finally {
    yukleniyor.value = false
  }
}

function islemSimgesi(turu: string): string {
  switch (turu) {
    case 'BASARILI_GIRIS': return '✅'
    case 'BASARISIZ_GIRIS': return '⚠️'
    case 'KAYIT_BASLATILDI': return '📧'
    case 'KVKK_ONAYLANDI_KAYIT_TAMAMLANDI': return '📝'
    case 'SIFRE_GUNCELENDI': return '🔑'
    case 'OTURUM_KAPATILDI': return '🚪'
    case 'TUM_OTURUMLAR_KAPATILDI': return '🚨'
    default: return '🛡️'
  }
}

function islemSinifi(turu: string): string {
  if (turu.includes('BASARILI') || turu.includes('TAMAMLANDI') || turu.includes('GUNCELENDI')) return 'sinif-basari'
  if (turu.includes('BASARISIZ') || turu.includes('HATALI') || turu.includes('TUM_OTURUMLAR')) return 'sinif-hata'
  return 'sinif-bilgi'
}

function islemEtiketi(turu: string): string {
  const harita: Record<string, string> = {
    BASARILI_GIRIS: 'Başarılı Giriş Yapıldı',
    BASARISIZ_GIRIS: 'Başarısız Giriş Denemesi',
    KAYIT_BASLATILDI: 'Kayıt ve KVKK Onayı Başlatıldı',
    KVKK_ONAYLANDI_KAYIT_TAMAMLANDI: 'KVKK Onaylandı & Kayıt Tamamlandı',
    SIFRE_SIFIRLAMA_KODU_ISTENDI: 'Şifre Sıfırlama Kodu İstendi',
    SIFRE_GUNCELENDI: 'Şifre Başarıyla Güncellendi',
    OTURUM_KAPATILDI: 'Oturum Kapatıldı',
    TUM_OTURUMLAR_KAPATILDI: 'Tüm Cihazlardaki Oturumlar Kapatıldı',
  }
  return harita[turu] ?? turu
}

function detayFormat(d: string): string {
  try {
    const obj = JSON.parse(d)
    if (obj.sebep) return `(${obj.sebep})`
    if (obj.hataliGirisSayaci) return `(${obj.hataliGirisSayaci}. hatalı deneme)`
    if (obj.email) return `(${obj.email})`
  } catch {
    /* ignore */
  }
  return d.length > 50 ? d.slice(0, 50) + '…' : d
}

function tarihFormat(tStr: string): string {
  try {
    const d = new Date(tStr)
    return d.toLocaleDateString('tr-TR', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
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
  max-width: 540px;
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

.log-hata {
  background: rgba(180, 95, 123, 0.15);
  border: 1px solid rgba(180, 95, 123, 0.3);
  color: #b45f7b;
  font-size: 0.84rem;
  padding: 10px 14px;
  border-radius: 8px;
  margin-top: 12px;
}

.log-yukleniyor {
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
  gap: 10px;
  max-height: 52vh;
}

.bos-log {
  text-align: center;
  color: #737d90;
  padding: 24px;
  font-size: 0.88rem;
}

.log-kart {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #f6f4fb;
  border: 1px solid #e5e7f0;
  border-radius: 12px;
  padding: 12px 14px;
}

.log-ikon-kutusu {
  width: 36px; height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
  flex-shrink: 0;
}

.sinif-basari {
  background: rgba(94, 169, 150, 0.15);
  border: 1px solid rgba(94, 169, 150, 0.3);
}

.sinif-hata {
  background: rgba(180, 95, 123, 0.15);
  border: 1px solid rgba(180, 95, 123, 0.3);
}

.sinif-bilgi {
  background: rgba(142, 137, 196, 0.15);
  border: 1px solid rgba(142, 137, 196, 0.3);
}

.log-detay {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.log-ust {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.islem-baslik {
  font-weight: 600;
  font-size: 0.86rem;
  color: #293042;
}

.log-tarih {
  font-size: 0.72rem;
  color: #737d90;
}

.log-alt {
  display: flex;
  gap: 10px;
  font-size: 0.76rem;
  color: #737d90;
}

.ip-etiket { font-family: monospace; color: #8572b7; }
.detay-metin { color: #737d90; }

.modal-alt-alan {
  padding-top: 16px;
  border-top: 1px solid #e5e7f0;
}

.btn-kapat-birincil {
  background: linear-gradient(135deg, #8e89c4, #b6a4da);
  color: #fff;
  font-weight: 700;
  width: 100%;
  padding: 11px;
  border-radius: 10px;
  border: none;
  cursor: pointer;
  box-shadow: 0 4px 20px rgba(142, 137, 196, 0.3);
}

.modal-fade-enter-active, .modal-fade-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.modal-fade-enter-from, .modal-fade-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>
