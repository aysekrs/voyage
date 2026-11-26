import { createError, getRouterParam } from 'h3'

export default defineEventHandler(async (event) => {
  const target = process.env.FASTAPI_URL || 'http://127.0.0.1:8000'
  const kod = String(getRouterParam(event, 'kod') || '').toUpperCase()
  if (!/^[A-Z]{3}$/.test(kod)) {
    throw createError({ statusCode: 400, message: 'Geçersiz havalimanı kodu.' })
  }
  try {
    return await $fetch(`${target}/airports/${kod}`, { retry: 0 })
  } catch (err: any) {
    throw createError({
      statusCode: err?.statusCode || err?.status || 502,
      message: err?.data?.detail || 'Havalimanı bulunamadı.'
    })
  }
})
