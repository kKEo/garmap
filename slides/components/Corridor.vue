<!--
  Schematic of the idea the whole tool rests on: a route, the corridor buffered
  around it, and the OSM extracts that corridor happens to straddle.

  Deliberately a diagram rather than a screenshot of `garmap preview` -- the real
  thing is a Leaflet map where the interesting part (a 6 km band) is a hairline
  at any zoom that also shows two countries.

  `:show-extracts="false"` drops the country boxes for the first, simplest telling.
-->
<template>
  <svg viewBox="0 0 480 260" class="corridor">
    <!-- The two Geofabrik extracts the corridor straddles. -->
    <g v-if="showExtracts">
      <rect x="8" y="8" width="300" height="150" class="extract" />
      <text x="18" y="28" class="extract-label">malopolskie</text>
      <rect x="120" y="120" width="352" height="132" class="extract" />
      <text x="360" y="242" class="extract-label">slovakia</text>
    </g>

    <!-- The buffered corridor: what actually gets downloaded and compiled. -->
    <path :d="path" class="band" />

    <!-- The route itself. -->
    <path :d="path" class="route" />

    <g v-if="showLabels">
      <line x1="196" y1="96" x2="196" y2="140" class="tick" />
      <text x="204" y="92" class="tick-label">--buffer</text>
    </g>
  </svg>
</template>

<script setup>
defineProps({
  showExtracts: { type: Boolean, default: true },
  showLabels: { type: Boolean, default: true },
})

// One wandering line, drawn twice: once fat and translucent for the corridor,
// once thin and solid for the route.
const path = 'M 40 200 C 110 190, 120 90, 196 118 S 300 190, 350 90 L 440 70'
</script>

<style scoped>
.corridor {
  width: 100%;
  height: auto;
}
.extract {
  fill: rgba(136, 136, 136, 0.1);
  stroke: #888;
  stroke-width: 1;
  stroke-dasharray: 5 4;
}
.extract-label {
  fill: #888;
  font-size: 11px;
  font-family: ui-monospace, SFMono-Regular, monospace;
}
.band {
  fill: none;
  stroke: #0050c8;
  stroke-opacity: 0.22;
  stroke-width: 44;
  stroke-linecap: round;
}
.route {
  fill: none;
  stroke: #e8112d;
  stroke-width: 3.5;
  stroke-linecap: round;
}
.tick {
  stroke: #0050c8;
  stroke-width: 1.5;
}
.tick-label {
  fill: #0050c8;
  font-size: 12px;
  font-family: ui-monospace, SFMono-Regular, monospace;
}
</style>
