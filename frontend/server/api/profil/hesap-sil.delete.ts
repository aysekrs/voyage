import { useRuntimeConfig } from '#imports'
export default defineEventHandler(async (event) => {
  const mevcutSifre = (await readBody<{ mevcutSifre?: string }>(event))?.mevcutSifre

  if (!mevcutSifre) {
    throw createError({
      statusCode: 400,
      message: 'Mevcut şifrenizi girmeniz gerekiyor.'
    })
  }

  const session = getCookie(event, 'voyage_session')

  if (!session) {
    throw createError({
      statusCode: 401,
      message: 'Oturum açmanız gerekiyor.'
    })
  }

  const config = useRuntimeConfig(event)

  try {
    const result = await $fetch<{ success: boolean; message: string }>(
      `${config.fastapiUrl}/auth/account`,
      {
        method: 'DELETE',
        headers: {
          cookie: `voyage_session=${session}`
        },
        body: {
          email: '',
          sifre: mevcutSifre
        }
      }
    )

    if (result.success) {
      deleteCookie(event, 'voyage_session', { path: '/' })
    }

    return result
  } catch (error: any) {
    const statusCode = error?.response?.status || 500
    const message =
      error?.data?.detail ||
      'Hesap silme işlemi gerçekleştirilemedi.'

    throw createError({
      statusCode,
      message
    })
  }
})

