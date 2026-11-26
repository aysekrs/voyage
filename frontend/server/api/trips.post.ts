
import { createError, getCookie, getHeader, getRequestURL, readBody } from 'h3'

export default defineEventHandler(async (event) => {
  const origin = getHeader(event, 'origin')
  const requestUrl = getRequestURL(event)

  if (origin && new URL(origin).origin !== requestUrl.origin) {
    throw createError({
      statusCode: 403,
      message: 'Geçersiz istek kaynağı.'
    })
  }

  const token = getCookie(event, 'voyage_session')

  if (!token) {
    throw createError({
      statusCode: 401,
      message: 'Oturum açılmamış.'
    })
  }

  const body = await readBody(event)
  const target = process.env.FASTAPI_URL || 'http://127.0.0.1:8000'

  try {
    return await $fetch(`${target}/trips`, {
      method: 'POST',
      body,
      headers: {
        cookie: `voyage_session=${encodeURIComponent(token)}`
      },
      retry: 0
    })
  } catch (err: any) {
    throw createError({
      statusCode: err?.statusCode || err?.status || 502,
      message: typeof err?.data?.detail === 'string'
        ? err.data.detail
        : 'Seyahat oluşturulamadı.'
    })
  }
})
