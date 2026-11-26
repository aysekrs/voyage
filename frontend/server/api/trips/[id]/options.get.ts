import {
  createError,
  getCookie,
  getRouterParam
} from 'h3'

// 5. Hafta: kayıtlı şehir önerilerini getir
export default defineEventHandler(async (event) => {

  const token = getCookie(event, 'voyage_session')

  if (!token) {
    throw createError({ statusCode: 401, message: 'Oturum açılmamış.' })
  }

  const id = getRouterParam(event, 'id')

  if (!id || !/^[1-9]\d*$/.test(id)) {
    throw createError({ statusCode: 400, message: 'Geçersiz seyahat ID.' })
  }

  const target = process.env.FASTAPI_URL || 'http://127.0.0.1:8000'

  try {
    return await $fetch(`${target}/trips/${id}/options`, {
      method: 'GET',
      headers: { cookie: `voyage_session=${encodeURIComponent(token)}` },
      retry: 0
    })
  } catch (err: any) {
    throw createError({
      statusCode: err?.statusCode || err?.status || 502,
      message: typeof err?.data?.detail === 'string'
        ? err.data.detail
        : 'Şehir önerileri alınamadı.'
    })
  }
})
