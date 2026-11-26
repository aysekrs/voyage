// FastAPI hatasını kullanıcıya gösterilecek tek bir Türkçe mesaja çevirir.
// detail bir metin olabilir ya da (alan doğrulama hatalarında) bir liste.
const ALAN_ADLARI: Record<string, string> = {
  title: 'Seyahat adı',
  destination: 'Gidilecek şehir',
  start_date: 'Gidiş tarihi',
  end_date: 'Dönüş tarihi',
  origin_city: 'Kalkış şehri',
  origin_airport_code: 'Havalimanı kodu',
  budget_try: 'Bütçe',
  people_count: 'Kişi sayısı',
  nature_weight: 'Doğa ağırlığı',
  food_weight: 'Yeme & içme ağırlığı',
  history_weight: 'Kültür & tarih ağırlığı',
  nightlife_weight: 'Gece hayatı ağırlığı'
}

export function fastapiHataMesaji(err: any, varsayilan: string): string {
  const detail = err?.data?.detail

  if (typeof detail === 'string') return detail

  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((d: any) => {
        const alan = Array.isArray(d?.loc) ? d.loc[d.loc.length - 1] : ''
        const ad = ALAN_ADLARI[alan] ?? ''
        const msg = String(d?.msg ?? '').replace(/^Value error, /, '')
        return ad ? `${ad}: ${msg}` : msg
      })
      .join(' ')
  }

  return varsayilan
}
