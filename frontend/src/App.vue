<script setup>
import { computed, nextTick, onMounted, ref } from "vue";
import L from "leaflet";

const categoryColors = {
  hospital: "#c93535",
  school: "#2e6fbd",
  pharmacy: "#d38a21",
  market: "#7950a6",
  park: "#328a55",
};

const provider = ref("auto");
const limit = ref(48);
const loading = ref(false);
const currentView = ref("dashboard");
const map = ref(null);
const layers = ref([]);
const center = ref({ lat: -15.839, lon: -48.025 });
const properties = ref([]);
const infrastructure = ref([]);
const dashboard = ref(null);
const notes = ref([]);
const selected = ref(null);
const graphStatus = ref({ enabled: false, connected: false, message: "Neo4j nao consultado." });

const topProperties = computed(() => properties.value.slice(0, 8));
const topValueProperties = computed(() => dashboard.value?.top_value_properties || []);
const propertyCount = computed(() => dashboard.value?.property_count ?? properties.value.length);
const averageQv = computed(() => {
  if (dashboard.value) return Number(dashboard.value.average_qv).toFixed(2);
  if (!properties.value.length) return "0.00";
  const total = properties.value.reduce((sum, property) => sum + property.qv, 0);
  return (total / properties.value.length).toFixed(2);
});
const graphLabel = computed(() => {
  if (!graphStatus.value.enabled) return "off";
  return graphStatus.value.connected ? "online" : "erro";
});

onMounted(() => {
  loadGraphStatus();
  loadData();
});

async function showMap() {
  currentView.value = "map";
  await nextTick();
  if (!map.value) {
    initMap();
  }
  renderMap();
  map.value.invalidateSize();
}

function showDashboard() {
  currentView.value = "dashboard";
}

function initMap() {
  map.value = L.map("map", { zoomControl: false }).setView([center.value.lat, center.value.lon], 14);
  L.control.zoom({ position: "bottomright" }).addTo(map.value);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap",
  }).addTo(map.value);
}

async function loadData() {
  loading.value = true;
  try {
    const response = await fetch(`/api/quality?provider=${provider.value}&limit=${limit.value}`);
    if (!response.ok) {
      const payload = await response.json();
      throw new Error(payload.detail || "Falha ao carregar dados");
    }

    const payload = await response.json();
    center.value = payload.center;
    properties.value = payload.properties;
    infrastructure.value = payload.infrastructure;
    dashboard.value = payload.dashboard;
    notes.value = payload.notes;
    selected.value = properties.value[0] || null;
    await loadGraphStatus();

    if (map.value) {
      await nextTick();
      renderMap();
    }
  } catch (error) {
    notes.value = [error.message];
  } finally {
    loading.value = false;
  }
}

async function loadGraphStatus() {
  try {
    const response = await fetch("/api/graph/status");
    graphStatus.value = await response.json();
  } catch (error) {
    graphStatus.value = {
      enabled: true,
      connected: false,
      message: error.message,
    };
  }
}

function renderMap() {
  if (!map.value) return;

  layers.value.forEach((layer) => layer.remove());
  layers.value = [];

  map.value.setView([center.value.lat, center.value.lon], 14);

  infrastructure.value.forEach((point) => {
    const layer = L.circleMarker([point.coords.lat, point.coords.lon], {
      radius: 6,
      color: categoryColors[point.category] || "#666",
      fillColor: categoryColors[point.category] || "#666",
      fillOpacity: 0.82,
      weight: 2,
    })
      .bindPopup(`<strong>${point.name}</strong><br>${categoryLabel(point.category)}`)
      .addTo(map.value);
    layers.value.push(layer);
  });

  properties.value.forEach((property) => {
    const layer = L.marker([property.coords.lat, property.coords.lon], {
      icon: propertyPinIcon(property),
    })
      .bindPopup(popupHtml(property))
      .on("click", () => {
        selected.value = property;
      })
      .addTo(map.value);
    layers.value.push(layer);
  });
}

function propertyPinIcon(property) {
  return L.divIcon({
    className: "property-marker",
    html: `<div class="property-pin" style="--pin-color:${qualityColor(property.qv)}"><span>${formatScore(property.qv)}</span></div>`,
    iconSize: [34, 44],
    iconAnchor: [17, 42],
    popupAnchor: [0, -38],
  });
}

async function focusProperty(property) {
  selected.value = property;
  if (currentView.value !== "map") {
    await showMap();
  }
  map.value.flyTo([property.coords.lat, property.coords.lon], 16, { duration: 0.6 });
}

function popupHtml(property) {
  return `
    <strong>${property.title}</strong><br>
    ${money(property.price)}<br>
    QV: ${formatScore(property.qv)}<br>
    IAR: ${formatScore(property.iar)}<br>
    Hospital mais perto: ${Math.round(property.nearest.hospital)} m<br>
    Escola mais perto: ${Math.round(property.nearest.school)} m
  `;
}

function categoryLabel(category) {
  return {
    hospital: "Hospital ou clinica",
    school: "Escola ou universidade",
    pharmacy: "Farmacia",
    market: "Mercado",
    park: "Parque ou lazer",
  }[category] || category;
}

function qualityColor(value) {
  if (value >= 0.75) return "#217a4b";
  if (value >= 0.5) return "#d19a2e";
  return "#d15b36";
}

function money(value) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatScore(value) {
  return Number(value).toFixed(2);
}
</script>

<template>
  <main v-if="currentView === 'dashboard'" class="dashboard-page">
    <header class="dashboard-header">
      <div class="brand">
        <span class="brand-mark"></span>
        <div>
          <h1>Aguas Claras</h1>
          <p>dashboard de qualidade de vida imobiliaria</p>
        </div>
      </div>
      <div class="dashboard-actions">
        <select v-model="provider" @change="loadData">
          <option value="auto">Auto</option>
          <option value="nestoria">Nestoria API</option>
          <option value="simulated">Simulado</option>
        </select>
        <button type="button" :disabled="loading" @click="loadData">
          {{ loading ? "Atualizando..." : "Atualizar" }}
        </button>
        <button type="button" class="primary-action" @click="showMap">
          Ver mapa
        </button>
      </div>
    </header>

    <section class="dashboard-metrics">
      <article>
        <span>Imoveis analisados</span>
        <strong>{{ propertyCount }}</strong>
      </article>
      <article>
        <span>Qualidade de vida media</span>
        <strong>{{ averageQv }}</strong>
      </article>
      <article>
        <span>Servicos urbanos</span>
        <strong>{{ infrastructure.length }}</strong>
      </article>
      <article>
        <span>Grafo Neo4j</span>
        <strong>{{ graphLabel }}</strong>
      </article>
    </section>

    <section class="dashboard-panel">
      <div class="panel-heading">
        <div>
          <span class="eyebrow">{{ dashboard?.query_source || "Ranking" }}</span>
          <h2>Top 5 custo-beneficio urbano</h2>
          <p>{{ dashboard?.query_description || "Ranking ponderado por QV, IAR e preco." }}</p>
        </div>
        <button type="button" @click="showMap">Abrir visualizacao do mapa</button>
      </div>

      <div class="value-list">
        <button
          v-for="(property, index) in topValueProperties"
          :key="property.id"
          type="button"
          @click="focusProperty(property)"
        >
          <span class="rank">{{ index + 1 }}</span>
          <span>
            <strong>{{ property.title }}</strong>
            <small>{{ money(property.price) }} · QV {{ formatScore(property.qv) }} · IAR {{ formatScore(property.iar) }}</small>
          </span>
          <b>{{ formatScore(property.composite_score) }}</b>
        </button>
      </div>
    </section>

    <section v-if="notes.length" class="notes dashboard-notes">
      <p v-for="note in notes" :key="note">{{ note }}</p>
    </section>
  </main>

  <div v-else class="map-shell">
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-mark"></span>
        <div>
          <h1>Aguas Claras</h1>
          <p>imoveis e qualidade de vida</p>
        </div>
      </div>

      <section class="controls">
        <label>
          Fonte dos imoveis
          <select v-model="provider" @change="loadData">
            <option value="auto">Auto</option>
            <option value="nestoria">Nestoria API</option>
            <option value="simulated">Simulado</option>
          </select>
        </label>

        <label>
          Quantidade
          <input v-model.number="limit" type="range" min="12" max="80" step="4" @change="loadData" />
        </label>

        <button type="button" class="secondary-action" @click="showDashboard">Voltar ao dashboard</button>

        <div class="metric-grid">
          <div>
            <strong>{{ propertyCount }}</strong>
            <span>imoveis</span>
          </div>
          <div>
            <strong>{{ infrastructure.length }}</strong>
            <span>servicos</span>
          </div>
          <div>
            <strong>{{ averageQv }}</strong>
            <span>QV media</span>
          </div>
          <div>
            <strong>{{ graphLabel }}</strong>
            <span>grafo</span>
          </div>
        </div>
      </section>

      <section class="legend">
        <span><i class="pin-sample"></i>Imovel</span>
        <span><i class="dot hospital"></i>Hospital</span>
        <span><i class="dot school"></i>Escola</span>
        <span><i class="dot pharmacy"></i>Farmacia</span>
        <span><i class="dot market"></i>Mercado</span>
        <span><i class="dot park"></i>Parque</span>
      </section>

      <section v-if="notes.length" class="notes">
        <p v-for="note in notes" :key="note">{{ note }}</p>
      </section>

      <section class="ranking">
        <h2>Melhores pontuacoes</h2>
        <button
          v-for="property in topProperties"
          :key="property.id"
          type="button"
          :class="{ active: selected?.id === property.id }"
          @click="focusProperty(property)"
        >
          <span>{{ property.title }}</span>
          <strong>{{ formatScore(property.qv) }}</strong>
        </button>
      </section>
    </aside>

    <main>
      <div class="topbar">
        <div>
          <span class="eyebrow">FastAPI + Vue + Leaflet + Neo4j</span>
          <h2>Mapa de atratividade residencial</h2>
        </div>
        <button type="button" :disabled="loading" @click="loadData">
          {{ loading ? "Atualizando..." : "Atualizar" }}
        </button>
      </div>

      <div id="map"></div>

      <section v-if="selected" class="details">
        <div>
          <span class="eyebrow">Imovel selecionado</span>
          <h3>{{ selected.title }}</h3>
          <p>{{ selected.address || "Aguas Claras, Brasilia - DF" }}</p>
        </div>
        <dl>
          <div>
            <dt>Preco</dt>
            <dd>{{ money(selected.price) }}</dd>
          </div>
          <div>
            <dt>Area</dt>
            <dd>{{ selected.area_m2 ? selected.area_m2 + " m2" : "N/D" }}</dd>
          </div>
          <div>
            <dt>QV</dt>
            <dd>{{ formatScore(selected.qv) }}</dd>
          </div>
          <div>
            <dt>IAR</dt>
            <dd>{{ formatScore(selected.iar) }}</dd>
          </div>
        </dl>
      </section>
    </main>
  </div>
</template>
