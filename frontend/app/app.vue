<template>

  <div :class="['sayfa', tema === 'light' ? 'theme-light' : 'theme-dark']">

    <!-- Tema Değiştirici Buton (Sağ Üst Sabit) -->

    <div class="tema-buton-konum">

      <ThemeToggle v-model="tema" />

    </div>

    <!-- ─── Yükleniyor ──────────────────────────────────────────── -->

    <div v-if="yukleniyor" class="kart yukle-kart">

      <div class="spinner"></div>

      <p class="yukle-yazi">Oturum kontrol ediliyor…</p>

    </div>

    <!-- ─── Giriş Yapılmış (Kullanıcı Paneli / Dashboard) ──────── -->

    <UserDashboard

      v-else-if="mevcutKullanici"

      :kullanici="mevcutKullanici"

      :islem="islem"

      @openProfile="profilModalAcik = true"

      @openSessions="oturumlarModalAcik = true"

      @openLogs="loglarModalAcik = true"

      @logout="cikisYap"

    />

    <!-- ─── Giriş / Kayıt ───────────────────────────────────────── -->

    <div v-else class="kart form-kart">

      <div class="travel-photo travel-photo-left" aria-hidden="true"></div>

      <div class="travel-photo travel-photo-right" aria-hidden="true"></div>

      <div class="flight-trail" aria-hidden="true">✈</div>

      <div class="voyage-brand" aria-label="VoyageAI">

        <div class="brand-star">✦</div>

        <h1 class="baslik"><span>Voyage</span><em>AI</em></h1>

        <p class="alt-baslik">HAYAL ET · PLANLA · KEŞFET</p>

      </div>

      <!-- Şifre Sıfırlama Formu -->

      <ResetPasswordForm

        v-if="sifreSifirlaAktif"

        @success="mesajGoster($event, 'basari')"

        @error="mesajGoster($event, 'hata')"

        @close="sifreSifirlaAktif = false"

      />

      <div v-else>

        <!-- Sekmeler -->

        <div class="sekme-grup">

          <button

            id="sekme-giris"

            class="sekme"

            :class="{ aktif: aktifSekme === 'giris' }"

            @click="aktifSekme = 'giris'; mesajTemizle()"

          >✈ &nbsp; Oturum Aç</button>

          <button

            id="sekme-kayit"

            class="sekme"

            :class="{ aktif: aktifSekme === 'kayit' }"

            @click="aktifSekme = 'kayit'; mesajTemizle()"

          >♙ &nbsp; Kayıt Ol</button>

          <div class="sekme-kayan" :class="{ sag: aktifSekme === 'kayit' }"></div>

        </div>

        <!-- Giriş Formu -->

        <LoginForm

          v-if="aktifSekme === 'giris'"

          @success="mesajGoster($event, 'basari')"

          @error="mesajGoster($event, 'hata')"

          @loginSuccess="onLoginSuccess"

          @forgotPassword="sifreSifirlaAc"

          @hataliGiris="onHataliGiris"

        />

        <!-- Kayıt Formu -->

        <RegisterForm

          v-if="aktifSekme === 'kayit'"

          @success="mesajGoster($event, 'basari')"

          @error="mesajGoster($event, 'hata')"

          @registered="onRegistered"

        />

      </div>

      <!-- Mesajlar -->

      <transition name="kayan">

        <div v-if="mesaj" :class="['mesaj', mesajTuru]" role="alert">

          <span class="mesaj-ikon">{{ mesajTuru === 'hata' ? '✕' : '✓' }}</span>

          {{ mesaj }}

        </div>

      </transition>

      <!-- 3 Hatalı Giriş Uyarısı -->

      <transition name="kayan">

        <div v-if="hataliGirisSayaci >= 3 && !sifreSifirlaAktif && !kullaniciAdiHatirlaAktif" class="mesaj kilitli-uyari" role="alert">

          <div class="kilitli-icerik">

            <span class="kilitli-ikon">🔒</span>

            <div>

              <strong>Çok fazla hatalı giriş!</strong>

              <p>Şifrenizi unuttuysanız sıfırlayabilirsiniz.</p>

            </div>

          </div>

          <button

            id="btn-sifre-sifirla-uyari"

            type="button"

            class="btn btn-turuncu btn-kucuk"

            @click="sifreSifirlaAc"

          >

            🔑 Şifremi Sıfırla

          </button>

        </div>

      </transition>

    </div>

    <!-- Aktif Oturumlar Modali -->

    <ActiveSessionsModal

      v-model="oturumlarModalAcik"

      @allRevoked="onAllSessionsRevoked"

      @sessionRevoked="onSessionRevoked"

    />

    <!-- Güvenlik Logları Modali -->

    <AuditLogsModal

      v-model="loglarModalAcik"

    />

    <!-- Profil Ayarları Modali -->

    <ProfileModal

      v-model="profilModalAcik"

    />

  </div>

</template>

<script setup lang="ts">

import { ref, onMounted, watch } from 'vue'

// ── Durum ──────────────────────────────────────────────────────────────

const mevcutKullanici           = ref<string | null>(null)

const yukleniyor                = ref(true)    // sayfa açılırken oturum kontrol edilir

const islem                     = ref(false)   // buton yüklenme durumu (çıkış yaparken)

const aktifSekme                = ref<'giris' | 'kayit'>('giris')

const mesaj                     = ref('')

const mesajTuru                 = ref<'hata' | 'basari'>('hata')

const sifreSifirlaAktif         = ref(false)   // şifre sıfırlama ekranı aktif mi

const kullaniciAdiHatirlaAktif  = ref(false)   // kullanıcı adı hatırlatma ekranı aktif mi

const oturumlarModalAcik        = ref(false)   // aktif oturumlar modali açık mı

const loglarModalAcik           = ref(false)   // güvenlik logları modali açık mı

const profilModalAcik           = ref(false)   // profil ayarları modali açık mı

const hataliGirisSayaci         = ref(0)       // 3'e ulaşınca şifre sıfırlama uyarısı gösterilir

const tema                      = ref<'dark' | 'light'>('dark')

function temaUygula(yeniTema: 'dark' | 'light') {

  if (!process.client) return

  localStorage.setItem('theme', yeniTema)

  if (yeniTema === 'light') {

    document.documentElement.classList.add('theme-light')

    document.documentElement.classList.remove('theme-dark')

    document.body.classList.add('theme-light')

    document.body.classList.remove('theme-dark')

  } else {

    document.documentElement.classList.add('theme-dark')

    document.documentElement.classList.remove('theme-light')

    document.body.classList.add('theme-dark')

    document.body.classList.remove('theme-light')

  }

}

onMounted(() => {

  if (process.client) {

    const saklananTema = localStorage.getItem('theme') as 'dark' | 'light' | null

    if (saklananTema === 'light' || saklananTema === 'dark') {

      tema.value = saklananTema

    }

    temaUygula(tema.value)

  }

})

watch(tema, (yeniTema) => {

  temaUygula(yeniTema)

})

let mesajZamanlayici: ReturnType<typeof setTimeout> | null = null

// ── Yardımcılar ────────────────────────────────────────────────────────

function mesajTemizle() {

  mesaj.value = ''

  if (mesajZamanlayici) {

    clearTimeout(mesajZamanlayici)

    mesajZamanlayici = null

  }

}

function mesajGoster(metin: string, tur: 'hata' | 'basari') {

  // Eski zamanlayıcı varsa temizle

  if (mesajZamanlayici) {

    clearTimeout(mesajZamanlayici)

  }

  mesaj.value   = metin

  mesajTuru.value = tur

  // 5 saniye sonra mesajı otomatik temizle

  mesajZamanlayici = setTimeout(() => {

    mesajTemizle()

  }, 5000)

}

// ── Sayfa yüklenince oturumu kontrol et ───────────────────────────────

onMounted(async () => {

  try {

    const veri = await $fetch<{ kullanici: string }>('/api/ben')

    mevcutKullanici.value = veri.kullanici

  } catch {

    mevcutKullanici.value = null

  } finally {

    yukleniyor.value = false

  }

})

// ── Olay Yönetimi (Event Handlers) ──────────────────────────────────────

function onLoginSuccess(kullanici: string) {

  mevcutKullanici.value   = kullanici

  hataliGirisSayaci.value = 0

  aktifSekme.value        = 'giris'

  mesajTemizle()

}

function onRegistered() {

  aktifSekme.value = 'giris'

  mesajTemizle()

}

function onHataliGiris(sayac: number) {

  hataliGirisSayaci.value = sayac

}

function sifreSifirlaAc() {

  sifreSifirlaAktif.value = true

  hataliGirisSayaci.value = 0 // uyarısını kapat

  mesajTemizle()

}

function onAllSessionsRevoked() {

  mevcutKullanici.value = null

  mesajGoster('Tüm cihazlardaki oturumlarınız sonlandırıldı.', 'basari')

}

function onSessionRevoked() {

  mesajGoster('Seçilen cihazın oturumu sonlandırıldı.', 'basari')

}

// ── Çıkış Yap ────────────────────────────────────────────────────────────

async function cikisYap() {

  islem.value = true

  try {

    await $fetch('/api/cikis', { method: 'POST' })

  } catch { /* sessizce geç */ }

  mevcutKullanici.value = null

  islem.value = false

}

</script>

<style>

/* ─── Genel Sıfırlama ─────────────────────────────────────────────── */

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {

  font-family: 'Inter', system-ui, sans-serif;

  background: #0a0e1a;

  min-height: 100vh;

  display: flex;

  align-items: center;

  justify-content: center;

}

/* ─── Arka Plan ───────────────────────────────────────────────────── */

.tema-buton-konum {

  position: fixed;

  top: 20px;

  right: 20px;

  z-index: 1000;

}

.sayfa {

  min-height: 100vh;

  width: 100%;

  display: flex;

  align-items: center;

  justify-content: center;

  background:

    radial-gradient(ellipse 80% 60% at 20% 20%, rgba(99, 102, 241, 0.18) 0%, transparent 60%),

    radial-gradient(ellipse 60% 40% at 80% 80%, rgba(16, 185, 129, 0.12) 0%, transparent 60%),

    #0a0e1a;

  padding: 24px;

}

/* ─── Kart ────────────────────────────────────────────────────────── */

.kart {

  width: 100%;

  max-width: 420px;

  background: rgba(255, 255, 255, 0.04);

  border: 1px solid rgba(255, 255, 255, 0.09);

  border-radius: 20px;

  padding: 40px 36px;

  backdrop-filter: blur(20px);

  box-shadow:

    0 0 0 1px rgba(99, 102, 241, 0.08),

    0 20px 60px rgba(0, 0, 0, 0.5),

    inset 0 1px 0 rgba(255, 255, 255, 0.06);

  animation: giris 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);

}

@keyframes giris {

  from { opacity: 0; transform: translateY(20px) scale(0.97); }

  to   { opacity: 1; transform: translateY(0)   scale(1); }

}

/* ─── Yükleniyor ─────────────────────────────────────────────────── */

.yukle-kart {

  display: flex;

  flex-direction: column;

  align-items: center;

  gap: 16px;

  padding: 48px;

}

.spinner {

  width: 40px; height: 40px;

  border: 3px solid rgba(255,255,255,0.08);

  border-top-color: #6366f1;

  border-radius: 50%;

  animation: don 0.7s linear infinite;

}

@keyframes don { to { transform: rotate(360deg); } }

.yukle-yazi { color: rgba(255,255,255,0.4); font-size: 0.9rem; }

/* ─── İçeri Kartı ────────────────────────────────────────────────── */

.iceri-kart {

  display: flex;

  flex-direction: column;

  align-items: center;

  text-align: center;

  gap: 16px;

}

.avatar {

  width: 72px; height: 72px;

  border-radius: 50%;

  background: linear-gradient(135deg, #6366f1, #10b981);

  font-size: 2rem; font-weight: 700;

  display: flex; align-items: center; justify-content: center;

  color: #fff;

  box-shadow: 0 0 30px rgba(99, 102, 241, 0.35);

}

.hosgeldin {

  font-size: 1.6rem;

  font-weight: 700;

  color: #fff;

}

.kullanici-adi {

  color: #6366f1;

  font-size: 1rem;

  font-weight: 600;

}

.bilet {

  display: flex;

  align-items: center;

  gap: 12px;

  background: rgba(16, 185, 129, 0.08);

  border: 1px solid rgba(16, 185, 129, 0.2);

  border-radius: 12px;

  padding: 14px 18px;

  width: 100%;

  text-align: left;

}

.bilet-ikon { font-size: 1.5rem; flex-shrink: 0; }

.bilet-bilgi {

  flex: 1;

  display: flex;

  flex-direction: column;

  gap: 2px;

}

.bilet-bilgi strong { color: #10b981; font-size: 0.9rem; }

.bilet-bilgi small  { color: rgba(255,255,255,0.4); font-size: 0.75rem; }

.bilet-ok {

  color: #10b981;

  font-size: 1.2rem;

  font-weight: 700;

}

.aciklama {

  color: rgba(255,255,255,0.35);

  font-size: 0.82rem;

  line-height: 1.6;

}

/* ─── Form Kartı ─────────────────────────────────────────────────── */

.logo {

  font-size: 2.5rem;

  text-align: center;

  margin-bottom: 4px;

  filter: drop-shadow(0 0 12px rgba(99,102,241,0.5));

}

.baslik {

  text-align: center;

  font-size: 1.6rem;

  font-weight: 800;

  color: #fff;

  margin-bottom: 4px;

}

.alt-baslik {

  text-align: center;

  color: rgba(255,255,255,0.35);

  font-size: 0.85rem;

  margin-bottom: 24px;

}

/* ─── Sekmeler ───────────────────────────────────────────────────── */

.sekme-grup {

  position: relative;

  display: flex;

  background: rgba(255,255,255,0.04);

  border-radius: 10px;

  padding: 4px;

  margin-bottom: 24px;

}

.sekme {

  flex: 1;

  border: none;

  background: transparent;

  color: rgba(255,255,255,0.4);

  font-size: 0.88rem;

  font-weight: 600;

  padding: 10px;

  border-radius: 8px;

  cursor: pointer;

  transition: color 0.25s;

  position: relative;

  z-index: 1;

}

.sekme.aktif { color: #fff; }

.sekme-kayan {

  position: absolute;

  top: 4px; left: 4px;

  width: calc(50% - 4px);

  height: calc(100% - 8px);

  background: rgba(99, 102, 241, 0.25);

  border: 1px solid rgba(99, 102, 241, 0.35);

  border-radius: 8px;

  transition: transform 0.28s cubic-bezier(0.34, 1.56, 0.64, 1);

}

.sekme-kayan.sag { transform: translateX(100%); }

/* ─── Form ───────────────────────────────────────────────────────── */

.form { display: flex; flex-direction: column; gap: 16px; }

.alan { display: flex; flex-direction: column; gap: 6px; }

.alan label {

  font-size: 0.8rem;

  font-weight: 600;

  color: rgba(255,255,255,0.5);

  text-transform: uppercase;

  letter-spacing: 0.06em;

}

.alan input {

  background: rgba(255,255,255,0.05);

  border: 1px solid rgba(255,255,255,0.1);

  border-radius: 10px;

  padding: 12px 14px;

  color: #fff;

  font-size: 0.95rem;

  outline: none;

  transition: border-color 0.2s, box-shadow 0.2s;

  width: 100%;

}

.alan input::placeholder { color: rgba(255,255,255,0.2); }

.alan input:focus {

  border-color: rgba(99, 102, 241, 0.6);

  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.12);

}

/* ─── Göz İkonlu Şifre Alanı ─────────────────────────────────────── */

.sifre-alan {

  position: relative;

  display: flex;

  align-items: center;

}

.sifre-alan input {

  padding-right: 44px; /* göz butonu için yer */

}

.goz-btn {

  position: absolute;

  right: 12px;

  top: 50%;

  transform: translateY(-50%);

  background: none;

  border: none;

  cursor: pointer;

  padding: 4px;

  color: rgba(255, 255, 255, 0.3);

  display: flex;

  align-items: center;

  justify-content: center;

  border-radius: 6px;

  transition: color 0.2s, **background** 0.2s;

  width: 28px;

  height: 28px;

  flex-shrink: 0;

}

.goz-btn:hover {

  color: rgba(255, 255, 255, 0.7);

  background: rgba(255, 255, 255, 0.06);

}

.goz-btn svg {

  width: 17px;

  height: 17px;

  pointer-events: none;

}

/* ─── Butonlar ───────────────────────────────────────────────────── */

.btn {

  border: none;

  border-radius: 10px;

  font-size: 0.95rem;

  font-weight: 700;

  cursor: pointer;

  padding: 13px 20px;

  width: 100%;

  transition: all 0.2s;

}

.btn:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-birincil {

  background: linear-gradient(135deg, #6366f1, #4f46e5);

  color: #fff;

  box-shadow: 0 4px 20px rgba(99, 102, 241, 0.3);

  margin-top: 4px;

}

.btn-birincil:not(:disabled):hover {

  transform: translateY(-1px);

  box-shadow: 0 6px 25px rgba(99, 102, 241, 0.45);

}

.btn-birincil:not(:disabled):active { transform: translateY(0); }

.btn-profil {

  background: rgba(245, 158, 11, 0.12);

  border: 1px solid rgba(245, 158, 11, 0.25);

  color: #fcd34d;

}

.btn-profil:not(:disabled):hover {

  background: rgba(245, 158, 11, 0.22);

  color: #fff;

}

.btn-oturumlar {

  background: rgba(99, 102, 241, 0.12);

  border: 1px solid rgba(99, 102, 241, 0.25);

  color: #a5b4fc;

}

.btn-oturumlar:not(:disabled):hover {

  background: rgba(99, 102, 241, 0.22);

  color: #fff;

}

.btn-loglar {

  background: rgba(16, 185, 129, 0.12);

  border: 1px solid rgba(16, 185, 129, 0.25);

  color: #6ee7b7;

}

.btn-loglar:not(:disabled):hover {

  background: rgba(16, 185, 129, 0.22);

  color: #fff;

}

.btn-cikis {

  background: rgba(239, 68, 68, 0.12);

  border: 1px solid rgba(239, 68, 68, 0.25);

  color: #ef4444;

}

.btn-cikis:not(:disabled):hover {

  background: rgba(239, 68, 68, 0.2);

}

/* ─── Mesaj ──────────────────────────────────────────────────────── */

.mesaj {

  display: flex;

  align-items: center;

  gap: 8px;

  border-radius: 10px;

  padding: 12px 14px;

  font-size: 0.875rem;

  font-weight: 500;

  margin-top: 4px;

}

.mesaj-ikon {

  width: 20px; height: 20px;

  border-radius: 50%;

  display: flex; align-items: center; justify-content: center;

  font-size: 0.7rem; font-weight: 800;

  flex-shrink: 0;

}

.hata {

  background: rgba(239, 68, 68, 0.1);

  border: 1px solid rgba(239, 68, 68, 0.25);

  color: #fca5a5;

}

.hata .mesaj-ikon {

  background: rgba(239, 68, 68, 0.2);

  color: #ef4444;

}

.basari {

  background: rgba(16, 185, 129, 0.1);

  border: 1px solid rgba(16, 185, 129, 0.25);

  color: #6ee7b7;

}

.basari .mesaj-ikon {

  background: rgba(16, 185, 129, 0.2);

  color: #10b981;

}

/* ─── Geçiş Animasyonu ───────────────────────────────────────────────── */

.kayan-enter-active, .kayan-leave-active {

  transition: all 0.25s ease;

}

.kayan-enter-from { opacity: 0; transform: translateY(-6px); }

.kayan-leave-to   { opacity: 0; transform: translateY(-6px); }

/* ─── Email Doğrulama Ekranı ─────────────────────────────────────────── */

.dogrulama-bilgi {

  display: flex;

  align-items: flex-start;

  gap: 12px;

  background: rgba(99, 102, 241, 0.08);

  border: 1px solid rgba(99, 102, 241, 0.2);

  border-radius: 12px;

  padding: 14px 16px;

}

.dogrulama-ikon {

  font-size: 1.4rem;

  flex-shrink: 0;

  line-height: 1.3;

}

.dogrulama-bilgi p {

  color: rgba(255, 255, 255, 0.55);

  font-size: 0.85rem;

  line-height: 1.5;

}

.dogrulama-bilgi strong {

  color: #a5b4fc;

  font-weight: 600;

}

/* Büyük, ortalanmış OTP kodu input */

.kod-input {

  text-align: center !important;

  font-size: 1.6rem !important;

  font-family: 'Courier New', monospace !important;

  letter-spacing: 10px !important;

  padding: 14px 10px !important;

}

.kod-input::placeholder {

  letter-spacing: 8px;

  font-size: 1.2rem;

}

/* Geri Dön butonu */

.btn-geri {

  background: transparent;

  border: 1px solid rgba(255, 255, 255, 0.1);

  color: rgba(255, 255, 255, 0.4);

  font-size: 0.85rem;

  font-weight: 500;

  padding: 10px;

  margin-top: -4px;

}

.btn-geri:hover {

  background: rgba(255, 255, 255, 0.05);

  color: rgba(255, 255, 255, 0.65);

}

/* Link Grubu ve Ayrac */

.link-grup {

  display: flex;

  align-items: center;

  justify-content: center;

  gap: 6px;

  margin-top: 4px;

}

.link-ayrac {

  color: rgba(255, 255, 255, 0.2);

  font-size: 0.8rem;

}

/* Şifremi / Kullanıcı Adımı Unuttum link butonu */

.btn-link {

  background: transparent;

  border: none;

  color: rgba(99, 102, 241, 0.7);

  font-size: 0.82rem;

  font-weight: 500;

  padding: 4px;

  cursor: pointer;

  transition: color 0.2s;

  text-decoration: underline;

  text-underline-offset: 3px;

}

.btn-link:hover {

  color: #a5b4fc;

}

/* Turuncu buton — şifre sıfırlama işlemleri */

.btn-turuncu {

  background: linear-gradient(135deg, #f97316, #ef4444);

  color: #fff;

  box-shadow: 0 4px 20px rgba(239, 68, 68, 0.3);

  margin-top: 4px;

}

.btn-turuncu:not(:disabled):hover {

  transform: translateY(-1px);

  box-shadow: 0 6px 25px rgba(239, 68, 68, 0.45);

}

.btn-turuncu:not(:disabled):active { transform: translateY(0); }

.btn-turuncu:disabled { opacity: 0.5; cursor: not-allowed; }

/* Küçük buton varyantı */

.btn-kucuk {

  padding: 8px 14px;

  font-size: 0.82rem;

  width: auto;

  margin-top: 0;

}

/* ─── 3 Hatalı Giriş Uyarı Kutusu ───────────────────────────────────── */

.kilitli-uyari {

  flex-direction: column;

  gap: 12px;

  background: rgba(239, 68, 68, 0.08);

  border: 1px solid rgba(239, 68, 68, 0.3);

  border-left: 3px solid #ef4444;

  color: #fca5a5;

  padding: 14px 16px;

}

.kilitli-icerik {

  display: flex;

  align-items: flex-start;

  gap: 10px;

  width: 100%;

}

.kilitli-ikon {

  font-size: 1.3rem;

  line-height: 1.2;

  flex-shrink: 0;

}

.kilitli-uyari strong {

  display: block;

  color: #fca5a5;

  font-size: 0.9rem;

  margin-bottom: 3px;

}

.kilitli-uyari p {

  color: rgba(252, 165, 165, 0.75);

  font-size: 0.82rem;

  margin: 0;

}

/* ─── Beni Hatırla Alanı ─────────────────────────────────────────── */

.hatirla-alan {

  display: inline-flex;

  align-items: center;

  gap: 8px;

  cursor: pointer;

  user-select: none;

  font-size: 0.88rem;

  color: rgba(255, 255, 255, 0.5);

  transition: color 0.2s;

  margin-top: 2px;

  margin-bottom: 2px;

}

.hatirla-alan:hover {

  color: rgba(255, 255, 255, 0.8);

}

.hatirla-alan input[type="checkbox"] {

  width: 16px;

  height: 16px;

  accent-color: #6366f1;

  cursor: pointer;

  margin: 0;

}

/* ─── Şifre Gücü Göstergesi ───────────────────────────────────────── */

.sifre-gucu {

  margin-top: 8px;

  display: flex;

  flex-direction: column;

  gap: 8px;

  animation: kayan 0.25s ease-out;

}

.guc-bar-arkaplan {

  width: 100%;

  height: 5px;

  background: rgba(255, 255, 255, 0.06);

  border-radius: 3px;

  overflow: hidden;

}

.guc-bar {

  height: 100%;

  border-radius: 3px;

  width: 0;

  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1), background-color 0.3s ease;

}

.guc-bar.seviye-1 {

  background: linear-gradient(90deg, #ef4444, #f87171);

}

.guc-bar.seviye-2 {

  background: linear-gradient(90deg, #f97316, #fb923c);

}

.guc-bar.seviye-3 {

  background: linear-gradient(90deg, #f59e0b, #fbbf24);

}

.guc-bar.seviye-4 {

  background: linear-gradient(90deg, #10b981, #34d399);

  box-shadow: 0 0 10px rgba(16, 185, 129, 0.4);

}

.guc-liste {

  list-style: none;

  display: flex;

  flex-direction: column;

  gap: 5px;

  padding: 0;

  margin: 0;

}

.guc-liste li {

  font-size: 0.8rem;

  color: rgba(255, 255, 255, 0.3);

  display: flex;

  align-items: center;

  gap: 6px;

  transition: color 0.2s ease, transform 0.2s ease;

}

.guc-liste li.gecirli {

  color: #a7f3d0;

  font-weight: 500;

  transform: translateX(2px);

}

.durum-ikon {

  font-size: 0.85rem;

  flex-shrink: 0;

  width: 12px;

  text-align: center;

}



/* VoyageAI travel identity — auth screens only */

.sayfa:has(.form-kart) {

  min-height: 100vh;

  padding: 55px 24px;

  overflow: hidden;

  position: relative;

  background:

    radial-gradient(ellipse at 90% 15%, rgba(180,214,247,.75), transparent 40%),

    radial-gradient(ellipse at 8% 82%, rgba(246,219,191,.72), transparent 40%),

    linear-gradient(135deg,#f9fbff 0%,#f0f5fb 54%,#fef9f3 100%);

}

.sayfa:has(.form-kart)::before {

  content: ''; position: absolute; inset: 0; pointer-events: none;

  background-image: repeating-linear-gradient(125deg,transparent 0 160px,rgba(97,129,178,.035) 161px 162px);

}

.sayfa .form-kart {

  position: relative; isolation: isolate; z-index: 1;

  width: min(100%, 540px); max-width: 540px;

  padding: clamp(28px,5vw,54px) clamp(24px,5vw,52px) 36px;

  border-radius: 32px;

  background: rgba(255,253,250,.96);

  border: 1px solid rgba(255,255,255,.94);

  box-shadow: 0 30px 95px rgba(39,65,102,.17), 0 0 0 1px rgba(54,83,124,.07);

  backdrop-filter: blur(14px);

  overflow: visible;

}

.voyage-brand { position: relative; text-align: center; margin: 4px 0 32px; }

.voyage-brand .baslik { color:#101d38; font-family: Georgia, 'Times New Roman', serif; font-weight: 700; letter-spacing: -2px; font-size: clamp(44px,7vw,65px); line-height: 1.08; margin: 0; }

.voyage-brand .baslik em { font-style: normal; color: #365ee9; }

.voyage-brand .alt-baslik { margin: 14px 0 0; font-size: 11px; font-weight: 800; letter-spacing: 4px; color: #77849a; }

.brand-star { position:absolute; right:15%; top:-16px; font-size:32px; color:#4165ef; }

.form-kart .sekme-grup { background: #f3f5f9; border: 1px solid #e2e7ef; padding:5px; border-radius:16px; margin-bottom: 30px; }

.form-kart .sekme { color:#52617b; font-size:15px; padding:14px 8px; border-radius:12px; font-weight:700; }

.form-kart .sekme.aktif { color: white; }

.form-kart .sekme-kayan { top:5px; left:5px; width:calc(50% - 5px); height:calc(100% - 10px); border:0; border-radius:12px; background:linear-gradient(115deg,#2454a8,#5b53f1); box-shadow:0 5px 16px rgba(50,79,173,.22); }

.form-kart .alan label { color:#35435e; }

.form-kart .alan input:not([type=checkbox]) { background:#fff; color:#14223d; border-color:#cdd7e6; }

.form-kart .alan input::placeholder { color:#8c9ab1; }

.form-kart .hatirla-alan { color:#34435c; }

.form-kart .btn-birincil { background:linear-gradient(110deg,#2253a4,#6853f5); box-shadow:0 14px 30px rgba(54,76,170,.22); border-radius:13px; padding:17px 20px; }

.form-kart .btn-link { color:#465bf2; }

.form-kart .mesaj.hata, .form-kart .kilitli-uyari { color:#a82e36; background:#fff1f1; }

.form-kart .mesaj.basari { color:#126c4d; background:#eafaf2; }

.form-kart .goz-btn { color:#7182a2; }

.form-kart .goz-btn:hover { color:#324a80; }

.form-kart .sayaç-metin { color:#b03c44; }

.travel-photo { position:absolute; z-index:-1; pointer-events:none; width:260px; height:330px; border:12px solid #fff; border-bottom-width:30px; border-radius:5px; background-size:cover; background-position:center; box-shadow:0 18px 45px rgba(43,65,89,.17); }

.travel-photo-left { left:-300px; top:100px; transform:rotate(-11deg); background-image:url('/voyage-coast.jpg'); }

.travel-photo-right { right:-300px; bottom:35px; transform:rotate(10deg); background-image:url('/voyage-coast.jpg'); background-position:right center; }

.flight-trail { position:absolute; z-index:-1; top:60px; right:-215px; font-size:70px; color:#749ad2; transform:rotate(-28deg); pointer-events:none; }

@media(max-width:1120px){.travel-photo {opacity:.25;} .travel-photo-left{left:-185px;} .travel-photo-right{right:-185px;} .flight-trail{display:none;} }

@media(max-width:620px){.sayfa:has(.form-kart){padding:24px 14px;} .sayfa .form-kart{padding:30px 22px;border-radius:23px;} .travel-photo{display:none;} .voyage-brand .alt-baslik{letter-spacing:2px;} }




/* ===== VoyageAI responsive + dual theme refinements ===== */
html, body, #__nuxt { width: 100%; min-height: 100%; }
html, body { margin: 0; overflow-x: clip; }
body { display: block; background: #f5f8ff; }
body.theme-dark { background: #0c1428; }
body.theme-light { background: #f5f8ff; }
.sayfa { width: 100%; min-width: 0; min-height: 100vh; min-height: 100dvh; padding: clamp(20px, 4vw, 56px) 20px; }
.sayfa:has(.form-kart) {
  display: flex; width: 100%; min-height: 100vh; min-height: 100dvh;
  padding: clamp(60px, 7vh, 84px) clamp(16px, 4vw, 60px);
  overflow: hidden; isolation: isolate; position: relative;
}
.sayfa.theme-light:has(.form-kart) {
  background:
    radial-gradient(ellipse 42% 62% at 7% 48%, rgba(132,186,232,.34), transparent 90%),
    radial-gradient(ellipse 45% 62% at 95% 70%, rgba(251,204,156,.32), transparent 90%),
    linear-gradient(120deg, #edf5fd 0%, #fbfdff 46%, #f5f1fc 100%);
}
.sayfa.theme-dark:has(.form-kart) {
  background:
    radial-gradient(ellipse 45% 65% at 5% 45%, rgba(45,86,153,.34), transparent 85%),
    radial-gradient(ellipse 45% 65% at 97% 72%, rgba(95,68,166,.26), transparent 85%),
    linear-gradient(120deg, #0b1428 0%, #121c37 55%, #16172e 100%);
}
.sayfa:has(.form-kart)::before { z-index: 0; opacity: .7; }
.sayfa.theme-dark:has(.form-kart)::before { opacity: .22; }
/* Wide screens: scenic panels outside the form, not overflowing the viewport. */
.sayfa:has(.form-kart)::after {
  content: ''; position: absolute; z-index: 0; pointer-events: none;
  width: clamp(210px, 25vw, 420px); height: clamp(290px, 34vw, 510px);
  left: max(24px, calc(50% - 750px)); top: 50%;
  transform: translateY(-52%) rotate(-6deg);
  border: 10px solid rgba(255,255,255,.92); border-bottom-width: 26px;
  border-radius: 10px;
  background: linear-gradient(160deg, rgba(37,91,175,.15), rgba(34,67,139,.04)), url('/voyage-coast.jpg') center / cover;
  box-shadow: 0 22px 70px rgba(35,55,100,.18);
}
.sayfa.theme-dark:has(.form-kart)::after {
  border-color: rgba(225,236,255,.82);
  box-shadow: 0 22px 80px rgba(0,0,0,.32);
}
.sayfa .form-kart {
  position: relative; z-index: 2; flex: 0 1 500px;
  width: min(100%, 500px); max-width: 500px;
  padding: clamp(28px, 3.4vw, 48px) clamp(22px, 3.3vw, 44px) 34px;
  border-radius: 28px;
}
.sayfa.theme-light .form-kart {
  background: rgba(255,254,253,.97);
  border: 1px solid rgba(255,255,255,.95);
  box-shadow: 0 24px 75px rgba(39,65,102,.16);
}
.sayfa.theme-dark .form-kart {
  background: rgba(20,31,55,.97);
  border: 1px solid rgba(152,176,223,.23);
  box-shadow: 0 28px 85px rgba(0,0,0,.38);
}
/* Keep original typefaces, branding and gradient buttons. */
.sayfa.theme-dark .voyage-brand .baslik { color: #f4f7ff; }
.sayfa.theme-dark .voyage-brand .baslik em { color: #8397ff; }
.sayfa.theme-dark .voyage-brand .alt-baslik { color: #b5c4df; }
.sayfa.theme-dark .brand-star { color: #a7b5ff; }
.sayfa.theme-dark .form-kart .sekme-grup { background: #202e4a; border-color: #35476b; }
.sayfa.theme-dark .form-kart .sekme { color: #c0cee5; }
.sayfa.theme-dark .form-kart .sekme.aktif { color: white; }
.sayfa.theme-dark .form-kart .alan label { color: #d4def0; }
.sayfa.theme-dark .form-kart .alan input:not([type=checkbox]) {
  background: #16233c; border-color: #455777; color: #f8fbff;
}
.sayfa.theme-dark .form-kart .alan input::placeholder { color: #9aabc6; }
.sayfa.theme-dark .form-kart .hatirla-alan { color: #d0daec; }
.sayfa.theme-dark .form-kart .btn-link { color: #b0baff; }
.sayfa.theme-dark .form-kart .goz-btn { color: #b4c5e3; }
.sayfa.theme-dark .form-kart .goz-btn:hover { color: #fff; }
.sayfa.theme-dark .form-kart .mesaj.hata, .sayfa.theme-dark .form-kart .kilitli-uyari {
  background: #3b202b; color: #ffc5ca;
}
.sayfa.theme-dark .form-kart .mesaj.basari { background: #153a34; color: #a8f3d6; }
.form-kart .alan input:not([type=checkbox]):focus-visible { border-color: #7786ff; box-shadow: 0 0 0 3px rgba(91,83,241,.18); }
.form-kart .sekme:focus-visible, .form-kart button:focus-visible { outline: 3px solid #93a5ff; outline-offset: 3px; }
.form-kart .form, .form-kart .alan { min-width: 0; }
.form-kart .alan input { min-width: 0; }
/* Original polaroid positions are clipped on desktop; use one safe scenic panel instead. */
.form-kart .travel-photo, .form-kart .flight-trail { display: none; }
.tema-buton-konum { top: clamp(12px,2vw,24px); right: clamp(12px,2vw,24px); }
@media (min-width: 1150px) {
  .sayfa:has(.form-kart) { padding-left: min(30vw, 460px); }
  .sayfa .form-kart { margin-left: auto; margin-right: auto; }
}
@media (min-width: 1600px) {
  .sayfa:has(.form-kart)::after { left: calc(50% - 690px); }
}
@media (max-width: 1149px) {
  .sayfa:has(.form-kart)::after { opacity: .28; left: -130px; }
}
@media (max-width: 800px) {
  .sayfa:has(.form-kart)::after { display: none; }
  .sayfa:has(.form-kart) { padding: 86px 20px 34px; }
  .sayfa .form-kart { width: min(100%, 540px); max-width: 540px; margin-inline: auto; }
}
@media (max-width: 480px) {
  .sayfa:has(.form-kart) { padding: 76px 12px 22px; align-items: flex-start; }
  .sayfa .form-kart { padding: 28px 20px 30px; border-radius: 22px; }
  .voyage-brand { margin-bottom: 24px; }
  .voyage-brand .baslik { font-size: clamp(40px, 12vw, 54px); }
  .voyage-brand .alt-baslik { font-size: 9px; letter-spacing: 2px; }
  .form-kart .sekme { font-size: 13px; padding: 12px 4px; }
  .form-kart .btn { max-width: 100%; }
}
@media (prefers-reduced-motion: reduce) {
  .sayfa .form-kart { animation: none; }
}

</style>
