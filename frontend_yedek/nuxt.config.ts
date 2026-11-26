import tailwindcss from '@tailwindcss/vite'

export default defineNuxtConfig({
  compatibilityDate: '2026-10-18',
  devtools: { enabled: true },
  pages: true,

  css: [
    '~/assets/css/kisi-b.css',
    '~/assets/css/main.css'
  ],

  vite: {
    plugins: [tailwindcss()]
  },

  runtimeConfig: {
    fastapiUrl: process.env.FASTAPI_URL || 'http://127.0.0.1:8000'
  }
})
