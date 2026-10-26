
<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from "vue";
import type { Map as LeafletMap } from "leaflet";

interface Durak {
  order: number;
  name: string;
  latitude: number;
  longitude: number;
}

const props = defineProps<{
  places: Durak[];
}>();

const haritaAlani = ref<HTMLElement | null>(null);

let L: typeof import("leaflet") | null = null;
let harita: LeafletMap | null = null;
let rotaKatmani: import("leaflet").LayerGroup | null = null;

function rotayiCiz() {
  if (!L || !harita || !rotaKatmani) return;

  rotaKatmani.clearLayers();

  const koordinatlar: [number, number][] = [];

  const siraliYerler = [...props.places]
    .filter(
      (yer) =>
        Number.isFinite(yer.latitude) &&
        Number.isFinite(yer.longitude) &&
        Math.abs(yer.latitude) <= 90 &&
        Math.abs(yer.longitude) <= 180
    )
    .sort((a, b) => a.order - b.order);

  for (const yer of siraliYerler) {
    const konum: [number, number] = [
      yer.latitude,
      yer.longitude
    ];

    koordinatlar.push(konum);

    const numara = L.divIcon({
      className: "",
      html: `
        <div style="
          width:32px;
          height:32px;
          display:flex;
          align-items:center;
          justify-content:center;
          border-radius:50%;
          background:#2563eb;
          border:3px solid white;
          color:white;
          font-weight:bold;
          box-shadow:0 2px 8px #0004;
        ">
          ${yer.order}
        </div>
      `,
      iconSize: [32, 32],
      iconAnchor: [16, 16]
    });

    const marker = L.marker(konum, { icon: numara });

    // Yer adını güvenli biçimde ekle.
    const popup = document.createElement("div");
    const baslik = document.createElement("strong");
    baslik.textContent = `${yer.order}. ${yer.name}`;
    popup.appendChild(baslik);

    marker.bindPopup(popup);
    rotaKatmani.addLayer(marker);
  }

  if (koordinatlar.length >= 2) {
    L.polyline(koordinatlar, {
      color: "#2563eb",
      weight: 4,
      opacity: 0.85
    }).addTo(rotaKatmani);

    harita.fitBounds(L.latLngBounds(koordinatlar), {
      padding: [45, 45],
      maxZoom: 15
    });
  } else if (koordinatlar.length === 1) {
    harita.setView(koordinatlar[0], 15);
  }
}

onMounted(async () => {
  L = await import("leaflet");
  await nextTick();

  if (!haritaAlani.value) return;

  harita = L.map(haritaAlani.value).setView(
    [41.0082, 28.9784],
    12
  );

  L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
      attribution: "&copy; OpenStreetMap contributors"
    }
  ).addTo(harita);

  rotaKatmani = L.layerGroup().addTo(harita);

  rotayiCiz();
});

watch(() => props.places, rotayiCiz);

onBeforeUnmount(() => {
  harita?.remove();
  harita = null;
  rotaKatmani = null;
});
</script>

<template>
  <div class="mt-6">
    <h4 class="mb-3 text-lg font-bold text-slate-800">
      🗺️ Günlük Rota Haritası
    </h4>

    <p class="mb-3 text-sm text-gray-500">
      Mavi numaralar ziyaret sırasını gösterir.
      Çizgiler kuş uçuşudur; gerçek yol tarifi değildir.
    </p>

    <div
      ref="haritaAlani"
      class="h-[400px] w-full rounded-xl border border-gray-200"
    />
  </div>
</template>
