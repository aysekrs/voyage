// Şehir fotoğrafları: tarayıcı doğrudan Vikipedi API'sine sorar
// (Wikimedia sunucudan gelen istekleri bot sayıp reddedebiliyor).
// Sonuçlar sayfalar arasında saklanır; her şehir için bir kez sorulur.
interface Foto {
  url: string | null
  page_url: string | null
}

const VIKIPEDI_API = 'https://tr.wikipedia.org/w/api.php'
const GENISLIK = 900

async function vikipedidenBul(baslik: string): Promise<Foto | null> {
  const veri = await $fetch<any>(VIKIPEDI_API, {
    query: {
      action: 'query',
      format: 'json',
      formatversion: 2,
      origin: '*', // tarayıcıdan (CORS) istek için gerekli
      redirects: 1,
      titles: baslik,
      prop: 'pageimages|pageprops|info',
      piprop: 'thumbnail',
      pithumbsize: GENISLIK,
      inprop: 'url'
    }
  })
  const sayfa = veri?.query?.pages?.[0]
  if (!sayfa || sayfa.missing || sayfa.pageprops?.disambiguation !== undefined) return null
  if (!sayfa.thumbnail?.source) return null
  return { url: sayfa.thumbnail.source, page_url: sayfa.fullurl ?? null }
}

export function useSehirFotografi() {
  const fotolar = useState<Record<number, Foto>>('sehir-fotolari', () => ({}))
  const bekleyen = useState<Record<number, boolean>>('sehir-foto-bekleyen', () => ({}))

  async function getir(id: number, sehirAdi: string, ulke?: string) {
    if (!import.meta.client) return
    if (fotolar.value[id] || bekleyen.value[id]) return
    bekleyen.value[id] = true
    try {
      const adaylar = ulke ? [sehirAdi, `${sehirAdi} (${ulke})`] : [sehirAdi]
      let bulunan: Foto | null = null
      for (const baslik of adaylar) {
        bulunan = await vikipedidenBul(baslik)
        if (bulunan) break
      }
      fotolar.value = { ...fotolar.value, [id]: bulunan ?? { url: null, page_url: null } }
    } catch {
      // ağ hatası: renkli zemin kalır, sonra tekrar denenebilir
    } finally {
      bekleyen.value[id] = false
    }
  }

  return { fotolar, getir }
}
