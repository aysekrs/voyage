
import { getCookie, createError } from 'h3'

export default defineEventHandler(async (event) => {
  const token = getCookie(event, 'voyage_session')

  if (!token) {
    throw createError({
      statusCode: 401,
      message: 'Oturum açılmamış.'
    })
  }

  const target = process.env.FASTAPI_URL || 'http://127.0.0.1:8000'

  try {
    return await $fetch(`${target}/trips`, {
      method: 'GET',
      headers: {
        cookie: `voyage_session=${encodeURIComponent(token)}`
      },
      retry: 0
    })
  } catch (err: any) {
    throw createError({
      statusCode: err?.statusCode || err?.status || 502,
      message: err?.data?.detail || 'Seyahatler alınamadı.'
    })
  }
})
