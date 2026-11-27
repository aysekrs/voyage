import { createError } from 'h3'

// Keşfet sayfası: şehirler + kategori sayıları
export default defineEventHandler(async () => {
  const target = process.env.FASTAPI_URL || 'http://127.0.0.1:8000'

  try {
    return await $fetch(`${target}/explore/cities`, { retry: 0 })
  } catch (err: any) {
    throw createError({
      statusCode: err?.statusCode || err?.status || 502,
      message: 'Şehirler alınamadı.'
    })
  }
})
