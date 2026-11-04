<!-- Copyright (c) 2026 Lumen Solutions
     SPDX-License-Identifier: AGPL-3.0-only
     Lumen Restaurants 0.1.0-r14: the floor plan's icons and the little
     drawings of its shapes and things, as in the approved mockup. Kept apart
     from LumenPOS's Icon.vue, so its updates never meet these. -->
<template>
  <span :class="art ? 'fart' : 'fic'" aria-hidden="true" v-html="svg" />
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  name: { type: String, required: true },
  // A shape or a thing on the plan (32 by 24), not an icon.
  art: { type: Boolean, default: false },
})

const IC = {
  bag: '<path d="M5.5 8h13l-1 13h-11l-1-13zM9 8V6.5a3 3 0 0 1 6 0V8"/>',
  scooter: '<circle cx="6" cy="17" r="2.5"/><circle cx="18" cy="17" r="2.5"/><path d="M8.5 17h7M15 17l-2-8h-3M13 9h3l3.5 8M4 12h6"/>',
  edit: '<path d="M4 20h4L19 9l-4-4L4 16v4zM13.5 6.5l4 4"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  minus: '<path d="M5 12h14"/>',
  close: '<path d="M6 6l12 12M18 6L6 18"/>',
  print: '<path d="M7 9V3h10v6M7 17H5a2 2 0 0 1-2-2v-4a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2h-2M7 14h10v7H7z"/>',
  pay: '<rect x="2.5" y="5" width="19" height="14" rx="2.5"/><path d="M2.5 10h19M6.5 15h4"/>',
  move: '<path d="M4 8h14l-3.5-3.5M20 16H6l3.5 3.5"/>',
  merge: '<path d="M6 3v4.5c0 3.5 6 4.5 6 8.5v5M18 3v4.5c0 3.5-6 4.5-6 8.5"/>',
  list: '<path d="M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01"/>',
  plan: '<rect x="3" y="3" width="18" height="18" rx="2.5"/><path d="M3 10h7v11M14 3v7h7"/>',
  image: '<rect x="3" y="4" width="18" height="16" rx="2.5"/><circle cx="9" cy="10" r="2"/><path d="M21 17l-5.5-5.5L6 20"/>',
  layers: '<path d="M12 3l9 5-9 5-9-5 9-5zM3 13l9 5 9-5"/>',
  rotL: '<path d="M3.5 4v5h5M4.3 9a8 8 0 1 1 1.6 8.3"/>',
  rotR: '<path d="M20.5 4v5h-5M19.7 9a8 8 0 1 0-1.6 8.3"/>',
  trash: '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
  person: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  chev: '<path d="M6 9l6 6 6-6"/>',
  receipt: '<path d="M6 3h12v18l-3-2-3 2-3-2-3 2V3zM9 8h6M9 12h6"/>',
  calendar: '<rect x="3.5" y="5" width="17" height="16" rx="2.5"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
}

const ART = {
  round: '<circle cx="16" cy="12" r="5.5"/><circle cx="16" cy="3.2" r="1.7"/><circle cx="16" cy="20.8" r="1.7"/><circle cx="7.2" cy="12" r="1.7"/><circle cx="24.8" cy="12" r="1.7"/>',
  square: '<rect x="10.5" y="6.5" width="11" height="11" rx="2"/><circle cx="16" cy="2.8" r="1.7"/><circle cx="16" cy="21.2" r="1.7"/><circle cx="6.8" cy="12" r="1.7"/><circle cx="25.2" cy="12" r="1.7"/>',
  rect: '<rect x="5" y="8.5" width="22" height="7" rx="2"/><circle cx="11" cy="4.5" r="1.7"/><circle cx="21" cy="4.5" r="1.7"/><circle cx="11" cy="19.5" r="1.7"/><circle cx="21" cy="19.5" r="1.7"/>',
  booth: '<path d="M7 21V5.5h18V21"/><path d="M9.5 21V8M22.5 21V8"/><rect x="12.5" y="10" width="7" height="9" rx="1.5"/>',
  wall: '<path d="M4 12h24" stroke-width="4"/>',
  door: '<path d="M6 19h20M8 19V9M8 9a10 10 0 0 1 10 10"/><path d="M24 19V9" opacity=".35"/>',
  window: '<path d="M4 9.5h24M4 14.5h24M4 9.5v5M28 9.5v5"/>',
  fence: '<path d="M4 12h24" stroke-dasharray="1.5 4" stroke-width="3"/>',
  plant: '<circle cx="16" cy="12" r="3"/><ellipse cx="16" cy="5" rx="2.4" ry="4"/><ellipse cx="16" cy="19" rx="2.4" ry="4"/><ellipse cx="9" cy="12" rx="4" ry="2.4"/><ellipse cx="23" cy="12" rx="4" ry="2.4"/>',
  cashier: '<rect x="6" y="9" width="20" height="11" rx="2"/><path d="M10 9V5h12v4M13 14h6"/>',
  kitchen: '<path d="M8 15a8 8 0 0 1 16 0zM6 18h20"/>',
  bar: '<path d="M11 20h10M16 14v6M10 5l6 7 6-7z"/>',
  wc: '<rect x="7" y="5" width="18" height="15" rx="2"/><path d="M16 5v15"/>',
  sink: '<path d="M7 11h18a9 9 0 0 1-18 0zM16 11V5h4"/>',
}
// The whole svg in one string, as LumenPOS's Icon.vue does: an svg's inner
// markup set apart from it is not reliably read as svg everywhere.
const svg = computed(() =>
  props.art
    ? `<svg viewBox="0 0 32 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${ART[props.name] || ''}</svg>`
    : `<svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${IC[props.name] || ''}</svg>`
)
</script>

<style scoped>
.fic, .fart { display: inline-flex; flex: none; line-height: 0; }
.fic { width: 18px; height: 18px; }
.fart { width: 28px; height: 22px; }
</style>
