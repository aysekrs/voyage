// Giriş yapmış kullanıcı bilgisi; üst bar ve sayfalar ortak kullanır.
export function useKullanici() {
  const kullanici = useState<string | null>('kullanici', () => null)
  const kontrolEdildi = useState<boolean>('kullanici-kontrol', () => false)

  async function yenile() {
    try {
      const veri = await $fetch<{ kullanici: string }>('/api/ben')
      kullanici.value = veri.kullanici
    } catch {
      kullanici.value = null
    } finally {
      kontrolEdildi.value = true
    }
    return kullanici.value
  }

  async function cikisYap() {
    try {
      await $fetch('/api/cikis', { method: 'POST' })
    } finally {
      kullanici.value = null
      await navigateTo('/login')
    }
  }

  return { kullanici, kontrolEdildi, yenile, cikisYap }
}
