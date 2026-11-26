import { createError, getRouterParam } from 'h3'

// Şehrin Vikipedi fotoğrafı (yoksa url: null)
export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')

  if (!id || !/^[1-9]\d*$/.test(id)) {
    throw createError({ statusCode: 400, message: 'Geçersiz şehir ID.' })
  }

  const target = process.env.FASTAPI_URL || 'http://127.0.0.1:8000'

  try {
    return await $fetch(`${target}/explore/cities/${id}/photo`, { retry: 0 })
  } catch {
    return { url: null, page_url: null }
  }
})
