
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
          background:linear-gradient(110deg,#789bd6 0%,#b6a4da 100%);
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
      color: "#8572b7",
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
  <div>
    <div ref="haritaAlani" class="b-harita" />
    <p class="b-not">Numaralar ziyaret sırasını gösterir. Çizgiler kuş uçuşudur; gerçek yol tarifi değildir.</p>
  </div>
</template>
