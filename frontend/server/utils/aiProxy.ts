import { createError, getCookie, getHeader, getRequestURL, readBody, type H3Event } from 'h3'

// AI asistan istekleri: oturum çerezini FastAPI'ye aktarır (5. hafta, Kişi B)
export async function aiProxy(event: H3Event, yol: string, method: 'GET' | 'POST' | 'DELETE', varsayilanHata: string) {
  if (method !== 'GET') {
    const origin = getHeader(event, 'origin')
    if (origin && new URL(origin).origin !== getRequestURL(event).origin) {
      throw createError({ statusCode: 403, message: 'Geçersiz istek kaynağı.' })
    }
  }
  const token = getCookie(event, 'voyage_session')
  if (!token) {
    throw createError({ statusCode: 401, message: 'Oturum açılmamış.' })
  }
  const target = process.env.FASTAPI_URL || 'http://127.0.0.1:8000'
  try {
    return await $fetch(`${target}/ai/${yol}`, {
      method,
      body: method === 'POST' ? await readBody(event) : undefined,
      headers: { cookie: `voyage_session=${encodeURIComponent(token)}` },
      // LLM cevabı sürebilir; yoğunlukta yedek modele geçiş dahil
      timeout: 45000,
      retry: 0
    })
  } catch (err: any) {
    throw createError({
      statusCode: err?.statusCode || err?.status || 502,
      message: fastapiHataMesaji(err, varsayilanHata)
    })
  }
}
