// Şehir fotoğraflarını bir kez çekip sayfalar arasında saklar.
interface Foto {
  url: string | null
  page_url: string | null
}

export function useSehirFotografi() {
  const fotolar = useState<Record<number, Foto>>('sehir-fotolari', () => ({}))
  const bekleyen = new Set<number>()

  async function getir(id: number) {
    if (fotolar.value[id] || bekleyen.has(id)) return
    bekleyen.add(id)
    try {
      const foto = await $fetch<Foto>(`/api/kesfet/${id}/foto`)
      fotolar.value = { ...fotolar.value, [id]: foto }
    } catch {
      // fotoğraf yoksa renkli zemin kalır
    } finally {
      bekleyen.delete(id)
    }
  }

  return { fotolar, getir }
}
