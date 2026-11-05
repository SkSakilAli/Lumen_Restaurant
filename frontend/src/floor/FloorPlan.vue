<!-- Copyright (c) 2026 Lumen Solutions
     SPDX-License-Identifier: AGPL-3.0-only
     Lumen Restaurants 0.1.0-r14: one area of the floor plan, drawn. It only
     draws and reports taps and drags; TablesView decides what they mean. -->
<template>
  <svg
    ref="svgEl"
    class="plan"
    :class="{ editing, picking }"
    :viewBox="VIEWBOX"
    preserveAspectRatio="xMidYMid meet"
    role="group"
    :aria-label="label"
    @pointerdown="down"
  >
    <defs>
      <pattern id="lr-plan-grid" width="20" height="20" patternUnits="userSpaceOnUse">
        <path class="grid-line" d="M20 0H0V20" />
      </pattern>
      <pattern id="lr-plan-hatch" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <rect class="hatch-bg" width="10" height="10" />
        <line class="hatch-line" x1="0" y1="0" x2="0" y2="10" />
      </pattern>
    </defs>
    <rect class="room-floor" x="30" y="30" width="940" height="560" />
    <image
      v-if="area.photo"
      :href="area.photo"
      x="30"
      y="30"
      width="940"
      height="560"
      preserveAspectRatio="xMidYMid meet"
      :opacity="(area.photo_opacity || 50) / 100"
    />
    <rect x="30" y="30" width="940" height="560" fill="url(#lr-plan-grid)" />

    <g
      v-for="f in area.objects"
      :key="f.key"
      class="fx"
      :class="['fx-' + f.kind, { selected: editing && selectedFx === f.key }]"
      data-kind="fx"
      :data-id="f.key"
      :transform="`translate(${f.x} ${f.y})`"
    >
      <g :transform="`rotate(${f.rot || 0})`">
        <rect v-if="f.kind === 'wall'" class="fx-wall" :x="-f.w / 2" :y="-f.h / 2" :width="f.w" :height="f.h" rx="1" />
        <line v-else-if="f.kind === 'fence'" class="fx-fence" :x1="-f.w / 2" y1="0" :x2="f.w / 2" y2="0" />
        <template v-else-if="f.kind === 'window'">
          <rect class="fx-window" :x="-f.w / 2" :y="-f.h / 2" :width="f.w" :height="f.h" />
          <line class="fx-window-line" :x1="-f.w / 2" y1="0" :x2="f.w / 2" y2="0" />
        </template>
        <template v-else-if="f.kind === 'door'">
          <rect class="fx-door-gap" :x="-f.w / 2" y="-7" :width="f.w" height="14" />
          <path class="fx-door-leaf" :d="`M${-f.w / 2} 0V${-f.w / 2}M${f.w / 2} 0V${-f.w / 2}`" />
          <path
            class="fx-door-arc"
            :d="`M${-f.w / 2} ${-f.w / 2}A${f.w / 2} ${f.w / 2} 0 0 1 0 0M${f.w / 2} ${-f.w / 2}A${f.w / 2} ${f.w / 2} 0 0 0 0 0`"
          />
        </template>
        <template v-else-if="f.kind === 'plant'">
          <ellipse v-for="i in 6" :key="i" class="fx-leaf" cx="0" cy="-12" rx="5" ry="9" :transform="`rotate(${i * 60})`" />
          <circle class="fx-plant-core" r="7" />
        </template>
        <rect
          v-else
          class="fx-box"
          :class="{ hatch: f.kind === 'kitchen' || f.kind === 'bar' }"
          :x="-f.w / 2"
          :y="-f.h / 2"
          :width="f.w"
          :height="f.h"
          rx="8"
        />
        <template v-if="editing">
          <rect v-if="f.kind === 'door'" class="fx-hit" v-bind="doorHit(f)" />
          <rect v-else class="fx-hit" v-bind="hit(f)" />
          <rect v-if="selectedFx === f.key" class="sel-outline" v-bind="outline(f)" rx="6" />
        </template>
      </g>
      <text v-if="fxLabel(f)" class="fx-label" v-bind="labelAt(f)" text-anchor="middle">{{ fxLabel(f) }}</text>
    </g>

    <g
      v-for="tb in tables"
      :key="tb.key"
      class="tbl"
      :class="['s-' + tb.status, { selected: tb.selected, eligible: tb.eligible }]"
      data-kind="table"
      :data-id="tb.key"
      :transform="`translate(${tb.x} ${tb.y})`"
      tabindex="0"
      role="button"
      :aria-label="tb.aria"
      @keydown.enter.prevent="$emit(editing ? 'pick' : 'tap', editing ? { kind: 'table', key: tb.key } : tb.key)"
      @keydown.space.prevent="$emit(editing ? 'pick' : 'tap', editing ? { kind: 'table', key: tb.key } : tb.key)"
    >
      <g :transform="`rotate(${tb.rot || 0})`">
        <circle v-if="parts(tb).ring.circle" class="ring" :r="parts(tb).ring.r" />
        <rect v-else class="ring" v-bind="box(parts(tb).ring)" />
        <rect
          v-for="(c, i) in parts(tb).chairs"
          :key="'c' + i"
          class="chair"
          x="-10"
          y="-6"
          width="20"
          height="12"
          rx="5"
          :transform="`translate(${c.x} ${c.y}) rotate(${c.rot})`"
        />
        <rect v-for="(b, i) in parts(tb).benches" :key="'b' + i" class="chair" v-bind="box(b)" />
        <circle v-if="parts(tb).top.circle" class="top" :r="parts(tb).top.r" />
        <rect v-else class="top" v-bind="box(parts(tb).top)" />
      </g>
      <text class="no" :y="tb.sub ? 1 : 7" text-anchor="middle">{{ tb.table_no }}</text>
      <text v-if="tb.sub" class="sub" y="17" text-anchor="middle">{{ tb.sub }}</text>
      <g v-if="tb.badge" class="badge-g" :class="'b-' + tb.badge.kind" :transform="`translate(0 ${-round1(parts(tb).hh)})`">
        <rect :x="-badgeWidth(tb.badge) / 2" y="-10" :width="badgeWidth(tb.badge)" height="20" rx="10" />
        <path v-if="tb.badge.kind === 'bill'" class="bdg-ic" :d="billIcon(tb.badge)" />
        <text :x="tb.badge.kind === 'bill' ? (rtl ? -6.5 : 6.5) : 0" y="4" text-anchor="middle">{{ tb.badge.text }}</text>
      </g>
    </g>
  </svg>
</template>

<script setup>
import { onUnmounted, ref } from 'vue'
import { t } from '../i18n'
import { BOXES, VIEWBOX, clamp, fxBounds, geom, snap } from './plan'

const props = defineProps({
  // { photo, photo_opacity, objects: [{ key, kind, x, y, w, h, rot, label }] }
  area: { type: Object, required: true },
  // [{ key, table_no, shape, seats, x, y, rot, status, sub, badge, aria, selected, eligible }]
  tables: { type: Array, required: true },
  editing: { type: Boolean, default: false },
  picking: { type: Boolean, default: false },
  selectedFx: { type: String, default: null },
  label: { type: String, default: '' },
  rtl: { type: Boolean, default: false },
})
const emit = defineEmits(['tap', 'pick', 'drag', 'blank'])

const svgEl = ref(null)
let drag = null

const round1 = (n) => Math.round(n * 10) / 10
const box = (b) => ({ x: b.x, y: b.y, width: b.w, height: b.h, rx: b.rx })
// One table's parts, worked out once per render of that table.
const cache = new WeakMap()
function parts(tb) {
  const key = `${tb.shape}|${tb.seats}|${tb.rot}`
  const hit = cache.get(tb)
  if (hit && hit.key === key) return hit.value
  const value = geom(tb)
  cache.set(tb, { key, value })
  return value
}

function hit(f) {
  const [w, h] = fxBounds(f)
  return { x: -w / 2, y: -h / 2, width: w, height: h }
}
function doorHit(f) {
  const [w, h] = fxBounds(f)
  return { x: -w / 2, y: -h + 8, width: w, height: h }
}
function outline(f) {
  const [w, h] = fxBounds(f)
  return f.kind === 'door'
    ? { x: -w / 2 - 4, y: -h + 4, width: w + 8, height: h + 8 }
    : { x: -w / 2 - 4, y: -h / 2 - 4, width: w + 8, height: h + 8 }
}
const BOX_LABEL = { cashier: 'Cashier', kitchen: 'Kitchen', bar: 'Bar', wc: 'Restrooms', sink: 'Hand wash' }
function fxLabel(f) {
  if (BOXES.has(f.kind)) return t(BOX_LABEL[f.kind])
  if (f.kind === 'door') return f.label || ''
  return ''
}
// A door's name sits on the room's side of it, whichever way it turns.
function labelAt(f) {
  if (f.kind !== 'door') return { x: 0, y: 5 }
  const a = ((f.rot || 0) * Math.PI) / 180
  return { x: round1(-Math.sin(a) * 24), y: round1(Math.cos(a) * 24 + 5) }
}

function badgeWidth(badge) {
  return Math.round(String(badge.text).length * 6.6 + 16 + (badge.kind === 'bill' ? 13 : 0))
}
function billIcon(badge) {
  const w = badgeWidth(badge)
  const ix = props.rtl ? w / 2 - 16 : -w / 2 + 7
  return `M${round1(ix)} -5.5h8v11l-2-1.3-2 1.3-2-1.3-2 1.3zM${round1(ix + 2.2)} -2h3.6M${round1(ix + 2.2)} 1h3.6`
}

// ---- taps and drags -------------------------------------------------------
function point(e) {
  const svg = svgEl.value
  const pt = svg.createSVGPoint()
  pt.x = e.clientX
  pt.y = e.clientY
  return pt.matrixTransform(svg.getScreenCTM().inverse())
}

function itemOf(kind, key) {
  return kind === 'table' ? props.tables.find((x) => x.key === key) : props.area.objects.find((x) => x.key === key)
}

function down(e) {
  if (e.button != null && e.button > 0) return
  const g = e.target.closest('[data-kind]')
  if (!g) {
    if (props.editing) emit('blank')
    return
  }
  if (!props.editing && g.dataset.kind !== 'table') return
  const item = itemOf(g.dataset.kind, g.dataset.id)
  if (!item) return
  const p = point(e)
  drag = { kind: g.dataset.kind, key: g.dataset.id, sx: p.x, sy: p.y, ox: item.x, oy: item.y, moved: false, pid: e.pointerId }
  if (props.editing) {
    e.preventDefault()
    g.classList.add('dragging')
    drag.el = g
  }
  window.addEventListener('pointermove', move)
  window.addEventListener('pointerup', up)
  window.addEventListener('pointercancel', cancel)
}

function move(e) {
  if (!drag || e.pointerId !== drag.pid) return
  const p = point(e)
  const dx = p.x - drag.sx
  const dy = p.y - drag.sy
  if (!drag.moved && Math.sqrt(dx * dx + dy * dy) < 5) return
  drag.moved = true
  if (!props.editing) return
  emit('drag', {
    kind: drag.kind,
    key: drag.key,
    x: clamp(snap(drag.ox + dx), 20, 980),
    y: clamp(snap(drag.oy + dy), 20, 615),
  })
}

function stop() {
  window.removeEventListener('pointermove', move)
  window.removeEventListener('pointerup', up)
  window.removeEventListener('pointercancel', cancel)
}

function up(e) {
  if (!drag || e.pointerId !== drag.pid) return
  const d = drag
  drag = null
  stop()
  d.el?.classList.remove('dragging')
  if (props.editing) emit('pick', { kind: d.kind, key: d.key })
  else if (!d.moved) emit('tap', d.key)
}

function cancel() {
  drag?.el?.classList.remove('dragging')
  drag = null
  stop()
}

onUnmounted(stop)
</script>

<style scoped>
.plan { display: block; width: 100%; height: 100%; min-height: 340px; user-select: none; -webkit-user-select: none; }
.plan text { font-family: inherit; }
.room-floor { fill: var(--floor); }
.grid-line { stroke: var(--floor-grid); stroke-width: 1; fill: none; }
.plan.editing .grid-line { stroke: var(--floor-grid-strong); }
.hatch-bg { fill: var(--fx-fill); }
.hatch-line { stroke: var(--fx-stroke); stroke-width: 1.4; }
.fx-wall { fill: var(--wall); }
.fx-fence { stroke: var(--wall); stroke-width: 5; stroke-dasharray: 2 8; stroke-linecap: round; fill: none; }
.fx-window { fill: var(--floor); stroke: var(--wall); stroke-width: 2; }
.fx-window-line { stroke: var(--wall); stroke-width: 1.2; }
.fx-door-gap { fill: var(--floor); }
.fx-door-leaf { stroke: var(--wall); stroke-width: 2.5; fill: none; stroke-linecap: round; }
.fx-door-arc { stroke: var(--wall); stroke-width: 1.2; stroke-dasharray: 4 4; fill: none; }
.fx-box { fill: var(--fx-fill); stroke: var(--fx-stroke); stroke-width: 1.5; }
.fx-box.hatch { fill: url(#lr-plan-hatch); }
.fx-leaf { fill: var(--plant); stroke: var(--plant-stroke); stroke-width: 1.1; }
.fx-plant-core { fill: var(--fx-fill); stroke: var(--plant-stroke); stroke-width: 1.1; }
.fx-label {
  fill: var(--fx-text);
  font-size: 13px;
  font-weight: 700;
  paint-order: stroke;
  stroke: var(--floor);
  stroke-width: 4px;
  stroke-linejoin: round;
}
.fx-hit { fill: transparent; }
.plan:not(.editing) .fx { pointer-events: none; }
.sel-outline { fill: none; stroke: var(--sel); stroke-width: 2; stroke-dasharray: 6 4; }

.tbl { cursor: pointer; }
.tbl:focus { outline: none; }
.tbl .ring { fill: transparent; stroke: none; }
.tbl .top { stroke-width: 2; }
.tbl .chair { stroke-width: 1.2; }
.tbl.s-free .top { fill: var(--t-free-fill); stroke: var(--t-free-stroke); }
.tbl.s-free .chair { fill: var(--chair); stroke: var(--t-free-stroke); }
.tbl.s-busy .top { fill: var(--t-busy-fill); stroke: var(--t-busy-stroke); }
.tbl.s-busy .chair { fill: var(--t-busy-chair); stroke: var(--t-busy-stroke); }
.tbl.s-bill .top { fill: var(--t-bill-fill); stroke: var(--t-bill-stroke); }
.tbl.s-bill .chair { fill: var(--t-bill-chair); stroke: var(--t-bill-stroke); }
.tbl.s-book .top { fill: var(--t-book-fill); stroke: var(--t-book-stroke); }
.tbl.s-book .chair { fill: var(--t-book-chair); stroke: var(--t-book-stroke); }
.tbl.s-to-clean .top { fill: var(--t-clean-fill); stroke: var(--t-clean-stroke); }
.tbl.s-to-clean .chair { fill: var(--t-clean-chair); stroke: var(--t-clean-stroke); }
.tbl.s-off .top,
.tbl.s-off .chair { fill: var(--surface-2); stroke: var(--t-free-stroke); stroke-dasharray: 5 4; }
.tbl .no { fill: var(--text); font-size: 19px; font-weight: 800; font-family: var(--font); }
.tbl.s-off .no { fill: var(--text-muted); }
.tbl .sub { fill: var(--text-muted); font-size: 11px; font-weight: 700; }
.badge-g rect { stroke: var(--floor); stroke-width: 2; }
.badge-g.b-busy rect { fill: var(--badge-busy); }
.badge-g.b-bill rect { fill: var(--badge-bill); }
.badge-g.b-book rect { fill: var(--badge-book); }
.badge-g.b-to-clean rect { fill: var(--badge-clean); }
.badge-g text { fill: #fff; font-size: 11px; font-weight: 700; }
.badge-g .bdg-ic { fill: none; stroke: #fff; stroke-width: 1.3; stroke-linejoin: round; stroke-linecap: round; }
.plan:not(.editing):not(.picking) .tbl:hover .ring { stroke: var(--border-strong); stroke-width: 2; }
.tbl:focus-visible .ring { stroke: var(--sel); stroke-width: 3; }
.tbl.selected .ring { stroke: var(--sel); stroke-width: 3; fill: var(--sel-fill); }
.plan.editing .tbl.selected .ring { stroke-width: 2; stroke-dasharray: 6 4; }
.plan.editing .tbl,
.plan.editing .fx { cursor: grab; touch-action: none; }
.plan.editing .dragging { cursor: grabbing; }
.plan.picking .tbl:not(.eligible),
.plan.picking .fx { opacity: 0.28; }
.plan.picking .tbl.eligible .ring {
  stroke: var(--sel);
  stroke-width: 3;
  stroke-dasharray: 7 6;
  animation: march 0.9s linear infinite;
}
@keyframes march { to { stroke-dashoffset: -26; } }
@media (prefers-reduced-motion: reduce) {
  .plan.picking .tbl.eligible .ring { animation: none; }
}
</style>
