import { createError, getQuery } from 'h3'

// Kalkış havalimanı araması (herkese açık; giriş gerekmez)
export default defineEventHandler(async (event) => {
  const target = process.env.FASTAPI_URL || 'http://127.0.0.1:8000'
  const { q = '' } = getQuery(event)
  try {
    return await $fetch(`${target}/airports`, { query: { q: String(q).slice(0, 60) }, retry: 0 })
  } catch (err: any) {
    throw createError({
      statusCode: err?.statusCode || err?.status || 502,
      message: 'Havalimanları alınamadı.'
    })
  }
})
