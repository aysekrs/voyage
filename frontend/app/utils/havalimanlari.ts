// Kalkış şehirleri ve havalimanı kodları (seyahat formu ve arama çubuğu ortak kullanır)
export const havalimanlari: Record<string, string> = {
  İstanbul: 'IST',
  Ankara: 'ESB',
  İzmir: 'ADB',
  Antalya: 'AYT',
  Adana: 'COV',
  Trabzon: 'TZX',
  Gaziantep: 'GZT',
  Kayseri: 'ASR',
  Diyarbakır: 'DIY',
  Samsun: 'SZF',
  Bodrum: 'BJV',
  Dalaman: 'DLM'
}

export const kategoriler = [
  { anahtar: 'history', deger: 'tarih', ad: 'Tarih', ikon: '🏛️' },
  { anahtar: 'nature', deger: 'doğa', ad: 'Doğa', ikon: '🌿' },
  { anahtar: 'food', deger: 'yemek', ad: 'Yemek', ikon: '🍽️' },
  { anahtar: 'nightlife', deger: 'gece_hayati', ad: 'Gece hayatı', ikon: '🌙' }
] as const

// Her şehre sabit bir pastel renk geçişi (fotoğraf yerine)
const GECISLER = [
  ['#dfe8fb', '#c9d8f4', '#b9c9ee'],
  ['#ece4f8', '#d9cdf0', '#c6b6e6'],
  ['#fbe3ec', '#f4cddc', '#ebb9cc'],
  ['#e2f2ec', '#cbe6dc', '#b5d9cb'],
  ['#fcecdc', '#f6dcc3', '#eecba9'],
  ['#e5eefb', '#e9dff6', '#f6dbe7']
]

export function sehirGecisi(id: number) {
  const [a, b, c] = GECISLER[Math.abs(id) % GECISLER.length]!
  return `radial-gradient(circle at 78% 22%, rgba(255,255,255,.75) 0 14%, transparent 15%), linear-gradient(140deg, ${a} 0%, ${b} 55%, ${c} 100%)`
}
