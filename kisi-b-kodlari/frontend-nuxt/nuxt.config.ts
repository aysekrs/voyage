// https://nuxt.com/docs/api/configuration/nuxt-config

import tailwindcss from "@tailwindcss/vite";

export default defineNuxtConfig({
  compatibilityDate: "2026-10-19",

  devtools: {
    enabled: true
  },

 css: [
  "~/assets/css/main.css",
  "leaflet/dist/leaflet.css"
],

  vite: {
    plugins: [tailwindcss()]
  }
});

