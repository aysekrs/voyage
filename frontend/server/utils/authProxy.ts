import { createError, getHeader, getCookie, getRequestURL, setHeader, readBody, type H3Event } from 'h3'

const target = process.env.FASTAPI_URL || 'http://127.0.0.1:8000'

export async function authProxy(event: H3Event, path: string, method: 'GET' | 'POST') {
  if (method === 'POST') {
    const origin = getHeader(event, 'origin')
    const requestUrl = getRequestURL(event)
    if (origin && new URL(origin).origin !== requestUrl.origin) {
      throw createError({ statusCode: 403, message: 'Geçersiz istek kaynağı.' })
    }
  }
  const token = getCookie(event, 'voyage_session')
  const cookie = token ? `voyage_session=${encodeURIComponent(token)}` : ''
  const body = method === 'POST' ? await readBody(event) : undefined
  try {
    const result = await $fetch.raw(`${target}/auth/${path}`, {
      method,
      body,
      headers: cookie ? { cookie } : {},
      retry: 0
    })
    const newCookie = result.headers.get('set-cookie')
    if (newCookie) setHeader(event, 'set-cookie', newCookie)
    return result._data
  } catch (err: any) {
    const detail = err?.data?.detail
    throw createError({
      statusCode: err?.statusCode || err?.status || 502,
      message: typeof detail === 'string' ? detail : 'Kimlik doğrulama servisine ulaşılamadı.'
    })
  }
}
