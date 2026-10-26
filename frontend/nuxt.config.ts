
export default defineNuxtConfig({
  compatibilityDate: '2026-10-18',
  devtools: { enabled: true },
  css: ['~/assets/css/main.css'],

  runtimeConfig: {
    fastapiUrl: process.env.FASTAPI_URL || 'http://127.0.0.1:8000'
  }
})
