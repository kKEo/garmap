<!--
  The six stages of `garmap build`, as a horizontal chain.

  `highlight` dims everything except the named stage, so the same component can
  carry both the overview slide and the per-stage walkthrough.

    <Pipeline />                      full chain, nothing dimmed
    <Pipeline highlight="split" />    just that stage lit
-->
<template>
  <div class="pipe">
    <template v-for="(stage, index) in stages" :key="stage.key">
      <div
        class="stage"
        :class="{ dim: highlight && highlight !== stage.key }"
      >
        <div class="stage-icon">{{ stage.icon }}</div>
        <div class="stage-name">{{ stage.name }}</div>
        <div class="stage-tool">{{ stage.tool }}</div>
      </div>
      <div v-if="index < stages.length - 1" class="arrow">&rarr;</div>
    </template>
  </div>
</template>

<script setup>
defineProps({
  highlight: { type: String, default: '' },
})

const stages = [
  { key: 'route', icon: '\u{1F4C4}', name: 'Route', tool: 'your .gpx' },
  { key: 'corridor', icon: '\u{1F4CD}', name: 'Corridor', tool: 'buffer' },
  { key: 'extracts', icon: '\u{2601}', name: 'Extracts', tool: 'Geofabrik' },
  { key: 'split', icon: '\u{2702}', name: 'Clip + split', tool: 'splitter' },
  { key: 'contours', icon: '\u{26F0}', name: 'Contours', tool: 'pyhgtmap' },
  { key: 'compile', icon: '\u{1F5FA}', name: 'Compile', tool: 'mkgmap' },
]
</script>

<style scoped>
.pipe {
  display: flex;
  align-items: stretch;
  justify-content: center;
  gap: 4px;
  flex-wrap: nowrap;
}
.stage {
  flex: 1 1 0;
  min-width: 0;
  padding: 10px 6px;
  border: 1px solid rgba(125, 145, 170, 0.45);
  border-radius: 8px;
  text-align: center;
  background: rgba(125, 145, 170, 0.08);
  transition: opacity 0.25s;
}
.stage.dim {
  opacity: 0.3;
}
.stage-icon {
  font-size: 1.5em;
  line-height: 1.2;
}
.stage-name {
  font-weight: 600;
  font-size: 0.82em;
}
.stage-tool {
  font-size: 0.68em;
  opacity: 0.75;
  font-family: ui-monospace, SFMono-Regular, monospace;
}
.arrow {
  display: flex;
  align-items: center;
  opacity: 0.45;
  font-size: 1.1em;
}
</style>
