
<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from "vue";
import type { Map as LeafletMap } from "leaflet";

interface HaritaYeri {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
  status: string;
}

const props = defineProps<{
  cityId: number | null;
  selectedPlaceId?: number | null;
}>();
const emit = defineEmits<{
  (e: "konumlarYuklendi", ids: number[]): void;
}>();

const apiUrl = "http://127.0.0.1:8001";

const haritaAlani = ref<HTMLElement | null>(null);
const yukleniyor = ref(false);
const hata = ref("");
const onayliSayisi = ref(0);
const adaySayisi = ref(0);

let L: typeof import("leaflet") | null = null;
let harita: LeafletMap | null = null;
let isaretciler: import("leaflet").LayerGroup | null = null;
let istekSirasi = 0;
const markerHaritasi = new Map<number, import("leaflet").CircleMarker>();

function haritayiTemizle() {
  isaretciler?.clearLayers();
  onayliSayisi.value = 0;
  adaySayisi.value = 0;
  markerHaritasi.clear();
  emit("konumlarYuklendi", []);
}

async function konumlariGetir() {
  const buIstek = ++istekSirasi;
  haritayiTemizle();
  hata.value = "";

  if (props.cityId === null || !L || !harita || !isaretciler) {
    return;
  }

  yukleniyor.value = true;

  try {
    const cevap = await fetch(
      `${apiUrl}/map/places?city_id=${props.cityId}`
    );

    if (!cevap.ok) {
      throw new Error(`API hatası: ${cevap.status}`);
    }

    const veri: {
      verified: HaritaYeri[];
      candidates: HaritaYeri[];
    } = await cevap.json();

    if (buIstek !== istekSirasi) return;

    const noktalar: import("leaflet").LatLngExpression[] = [];

    function yerleriEkle(
      yerler: HaritaYeri[],
      renk: string,
      durum: string
    ) {
      for (const yer of yerler) {
        if (
          !Number.isFinite(yer.latitude) ||
          !Number.isFinite(yer.longitude) ||
          Math.abs(yer.latitude) > 90 ||
          Math.abs(yer.longitude) > 180
        ) {
          continue;
        }

        const konum: import("leaflet").LatLngExpression = [
          yer.latitude,
          yer.longitude
        ];

        const marker = L!.circleMarker(konum, {
          radius: 8,
          color: renk,
          fillColor: renk,
          fillOpacity: 0.8
        });

        // API'den gelen isimleri HTML olarak işlemiyoruz.
        const popup = document.createElement("div");
        const baslik = document.createElement("strong");
        baslik.textContent = yer.name;

        const aciklama = document.createElement("p");
        aciklama.textContent = durum;

        popup.append(baslik, aciklama);

        marker.bindPopup(popup);
marker.addTo(isaretciler!);

markerHaritasi.set(yer.id, marker);

noktalar.push(konum);
      }
    }

    yerleriEkle(
      veri.verified,
      "#16a34a",
      "Veritabanında kayıtlı konum"
    );

    yerleriEkle(
      veri.candidates,
      "#f97316",
      "Geoapify adayı - henüz doğrulanmadı"
    );

    onayliSayisi.value = veri.verified.length;
    adaySayisi.value = veri.candidates.length;
    emit(
  "konumlarYuklendi",
  [...veri.verified, ...veri.candidates].map(yer => yer.id)
);

    await nextTick();

    

    if (noktalar.length > 0) {
      harita.fitBounds(L.latLngBounds(noktalar), {
        padding: [35, 35],
        maxZoom: 14
      });

      secilenYeriGoster();
    }
  } catch (error) {
    if (buIstek !== istekSirasi) return;

    hata.value = "Harita verileri yüklenemedi.";
    console.error(error);
  } finally {
    if (buIstek === istekSirasi) {
      yukleniyor.value = false;
    }
  }
}


onMounted(async () => {
  // Leaflet tarayıcı ortamında yüklenecek.
  L = await import("leaflet");

  if (!haritaAlani.value) return;

  harita = L.map(haritaAlani.value).setView(
    [41.0082, 28.9784],
    5
  );

  L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
      attribution:
        '&copy; OpenStreetMap contributors'
    }
  ).addTo(harita);

  isaretciler = L.layerGroup().addTo(harita);

  await konumlariGetir();
});

watch(() => props.cityId, konumlariGetir);

onBeforeUnmount(() => {
  istekSirasi++;
  harita?.remove();
  harita = null;
});

function secilenYeriGoster() {
  if (
    !L ||
    !harita ||
    props.selectedPlaceId == null
  ) {
    return;
  }

  const marker = markerHaritasi.get(
    props.selectedPlaceId
  );

  if (!marker) return;

  const konum = marker.getLatLng();

  harita.setView(konum, 15, {
    animate: true
  });

  marker.openPopup();

  haritaAlani.value?.scrollIntoView({
    behavior: "smooth",
    block: "center"
  });
}

watch(
  () => props.selectedPlaceId,
  secilenYeriGoster
);

</script>

<template>
  <section class="mt-10 rounded-2xl bg-white p-6 shadow">
    <h2 class="text-2xl font-bold text-slate-800">
      🗺️ Gezilecek Yerler Haritası
    </h2>

    <p class="mt-2 text-gray-600">
      Yeşil noktalar kayıtlı koordinatları, turuncu noktalar
      henüz doğrulanmamış Geoapify adaylarını gösterir.
    </p>

    <div class="mt-4 flex flex-wrap gap-4 text-sm">
      <span class="font-medium text-green-700">
        ● Kayıtlı: {{ onayliSayisi }}
      </span>

      <span class="font-medium text-orange-600">
        ● Aday: {{ adaySayisi }}
      </span>
    </div>

    <p v-if="yukleniyor" class="mt-3 text-blue-600">
      Konumlar yükleniyor...
    </p>

    <p v-if="hata" class="mt-3 text-red-600">
      {{ hata }}
    </p>

    <ClientOnly>
      <div
        ref="haritaAlani"
        class="mt-5 h-[440px] w-full rounded-xl border border-gray-200"
      />
    </ClientOnly>

    <p class="mt-4 text-xs text-gray-500">
      Bu harita bir prototiptir. Turuncu noktalar doğrulanmış
      ziyaret veya rota başlangıç noktaları değildir.
    </p>
  </section>
</template>
