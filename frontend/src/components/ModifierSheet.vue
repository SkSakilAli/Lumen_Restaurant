<!-- Copyright (c) 2026 Lumen Solutions
     SPDX-License-Identifier: AGPL-3.0-only
     "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md. -->
<!-- Lumen Restaurants: the window a dish opens at the till, its add-on groups
     as chips (one choice or several, required, a limit), a note for the
     kitchen and the quantity. A paid choice shows its price; the button shows
     the dish with its paid choices. Once the kitchen has a line its choices
     stay as they are: more of the same can still be added. -->
<template>
  <div class="ms-backdrop" @click.self="$emit('close')" @keydown.esc="$emit('close')">
    <div ref="sheet" class="ms-sheet" role="dialog" aria-modal="true" :aria-label="item.item_name">
      <header class="ms-head">
        <span class="ms-ph">
          <img v-if="item.image" :src="item.image" alt="" />
          <template v-else>{{ (item.item_name || '?').trim().charAt(0) }}</template>
        </span>
        <div class="ms-title">
          <b>{{ item.item_name }}</b>
          <span class="muted small">{{ money(item.price) }}</span>
        </div>
        <button class="ms-x" :aria-label="t('Close')" @click="$emit('close')"><Icon name="close" /></button>
      </header>

      <div class="ms-body">
        <p v-if="locked" class="ms-locked">
          {{ t('The kitchen already has this dish, its choices stay as they are. Change the quantity, or add it again with other choices.') }}
        </p>
        <section v-for="g in groups" :key="g.name" class="ms-group">
          <div class="ms-ghead">
            <b>{{ g.title }}</b>
            <span class="ms-tag" :class="g.multiple ? 'many' : 'one'">
              {{ g.multiple ? (g.max ? t('Up to {n}', { n: g.max }) : t('Pick any')) : t('Pick one') }}
            </span>
            <span v-if="g.required" class="ms-tag req">{{ t('Required') }}</span>
          </div>
          <div class="ms-chips">
            <button
              v-for="o in g.options"
              :key="o.id"
              class="ms-chip"
              :aria-pressed="isOn(g, o) ? 'true' : 'false'"
              :disabled="locked || (!isOn(g, o) && isFull(g))"
              @click="toggle(g, o)"
            >
              {{ o.title }}
              <span v-if="o.item_code && o.price > 0" class="ms-plus">+{{ amount(o.price) }}</span>
            </button>
          </div>
        </section>
        <label class="ms-note">
          <span>{{ t('Note for the kitchen') }}</span>
          <input v-model="note" :disabled="locked" :placeholder="t('No onions, well done, on the side…')" />
        </label>
      </div>

      <footer class="ms-foot">
        <div class="stepper">
          <button :aria-label="t('Less')" @click="qty = Math.max(1, qty - 1)">-</button>
          <b>{{ qty }}</b>
          <button :aria-label="t('More')" @click="qty++">+</button>
        </div>
        <button v-if="editing" class="ms-remove" @click="$emit('remove')">{{ t('Remove') }}</button>
        <span class="ms-need">
          {{ missing.length ? t('Choose from: {g}', { g: missing.map((g) => g.title).join(listSep) }) : '' }}
        </span>
        <button class="btn btn-primary ms-go" :disabled="missing.length > 0" @click="save">
          {{ editing ? t('Save changes') : t('Add to order') }} · {{ money(unitPrice(item, groups, picks) * qty) }}
        </button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import Icon from './Icon.vue'
import { money } from '../format'
import { t, locale } from '../i18n'
import { missingGroups, unitPrice } from '../addons'

const props = defineProps({
  item: { type: Object, required: true },
  groups: { type: Array, required: true },
  initialPicks: { type: Object, default: () => ({}) },
  initialQty: { type: Number, default: 1 },
  initialNote: { type: String, default: '' },
  editing: { type: Boolean, default: false },
  locked: { type: Boolean, default: false },
})
const emit = defineEmits(['save', 'remove', 'close'])

const picks = ref(JSON.parse(JSON.stringify(props.initialPicks || {})))
const qty = ref(props.initialQty || 1)
const note = ref(props.initialNote || '')
const sheet = ref(null)
// An Arabic list is joined with an Arabic comma.
const listSep = computed(() => (locale.value === 'ar' ? '، ' : ', '))

const missing = computed(() => (props.locked ? [] : missingGroups(props.groups, picks.value)))

function amount(value) {
  return (Number(value) || 0).toFixed(2)
}

function isOn(g, o) {
  return (picks.value[g.name] || []).includes(o.id)
}

function isFull(g) {
  return g.multiple && g.max > 0 && (picks.value[g.name] || []).length >= g.max
}

function toggle(g, o) {
  const current = picks.value[g.name] || []
  if (!g.multiple) {
    // One choice: tapping the picked one again clears it, unless it is required.
    picks.value = { ...picks.value, [g.name]: current.includes(o.id) && !g.required ? [] : [o.id] }
    return
  }
  if (current.includes(o.id)) {
    picks.value = { ...picks.value, [g.name]: current.filter((id) => id !== o.id) }
  } else if (!isFull(g)) {
    const order = g.options.map((x) => x.id)
    picks.value = {
      ...picks.value,
      [g.name]: [...current, o.id].sort((a, b) => order.indexOf(a) - order.indexOf(b)),
    }
  }
}

function save() {
  if (missing.value.length) return
  emit('save', { picks: picks.value, qty: qty.value, note: note.value })
}

onMounted(() => {
  const first = sheet.value?.querySelector('.ms-chip:not([disabled])') || sheet.value?.querySelector('input')
  first?.focus()
})
</script>

<style scoped>
.ms-backdrop {
  position: fixed; inset: 0; z-index: 60; background: rgba(8, 12, 22, 0.55);
  display: grid; place-items: center; padding: 16px;
}
.ms-sheet {
  width: min(580px, 100%); max-height: min(88vh, 760px); display: flex; flex-direction: column;
  background: var(--card-bg); color: var(--text); border-radius: var(--radius-lg); box-shadow: var(--shadow-md); overflow: hidden;
}
.ms-head { display: flex; gap: 12px; align-items: center; padding: 14px 16px; border-bottom: 1px solid var(--border); }
.ms-ph {
  width: 44px; height: 44px; border-radius: 12px; flex: none; display: grid; place-items: center; overflow: hidden;
  background: rgba(20, 99, 255, 0.1); color: var(--brand-dark); font-weight: 800; font-size: 18px;
}
.ms-ph img { width: 100%; height: 100%; object-fit: cover; }
.ms-title { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.ms-title b { font-size: 16px; }
.ms-x { border: 0; background: var(--surface-2); color: var(--text); width: 36px; height: 36px; border-radius: 10px; display: grid; place-items: center; cursor: pointer; }
.ms-body { padding: 4px 16px 14px; overflow: auto; display: flex; flex-direction: column; gap: 14px; }
.ms-locked {
  margin: 10px 0 0; padding: 9px 12px; border-radius: 10px; font-size: 13px;
  background: color-mix(in srgb, var(--amber) 14%, transparent); color: var(--text);
}
.ms-group { display: flex; flex-direction: column; gap: 8px; padding-top: 10px; }
.ms-ghead { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.ms-ghead b { font-size: 14px; margin-inline-end: 4px; }
.ms-tag { font-size: 11.5px; font-weight: 700; padding: 2px 8px; border-radius: 999px; background: var(--surface-2); color: var(--text-muted); }
.ms-tag.one { background: color-mix(in srgb, var(--promo) 14%, transparent); color: var(--promo); }
.ms-tag.many { background: color-mix(in srgb, var(--brand) 12%, transparent); color: var(--brand-dark); }
.ms-tag.req { background: color-mix(in srgb, var(--amber) 16%, transparent); color: var(--amber); }
.ms-chips { display: flex; flex-wrap: wrap; gap: 7px; }
.ms-chip {
  border: 1.5px solid var(--border); background: var(--card-bg); color: var(--text); border-radius: 999px;
  padding: 8px 14px; font: inherit; font-size: 13.5px; font-weight: 600; cursor: pointer; display: inline-flex; gap: 6px; align-items: center;
}
.ms-chip[aria-pressed='true'] { background: var(--brand); border-color: var(--brand); color: #fff; }
.ms-chip:disabled { opacity: 0.45; cursor: not-allowed; }
.ms-plus { font-size: 12px; opacity: 0.85; font-variant-numeric: tabular-nums; }
.ms-note { display: flex; flex-direction: column; gap: 5px; font-size: 12.5px; font-weight: 700; color: var(--text-muted); }
.ms-note input { padding: 10px 12px; border: 1px solid var(--border); border-radius: 10px; font: inherit; font-size: 14px; background: var(--input-bg); color: var(--text); }
.ms-foot { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; padding: 12px 16px; border-top: 1px solid var(--border); }
.stepper { display: flex; align-items: center; gap: 2px; border: 1.5px solid var(--border); border-radius: 10px; overflow: hidden; }
.stepper button { width: 38px; height: 38px; border: 0; background: transparent; font-size: 18px; font-weight: 700; cursor: pointer; color: var(--text); }
.stepper b { min-width: 28px; text-align: center; }
.ms-remove { border: 0; background: transparent; color: var(--red); font: inherit; font-weight: 700; cursor: pointer; padding: 8px; }
.ms-need { flex: 1; min-width: 120px; font-size: 12.5px; color: var(--text-muted); }
.ms-go { padding: 12px 16px; font-size: 15px; }
@media (max-width: 720px) {
  .ms-backdrop { place-items: end center; padding: 0; }
  .ms-sheet { border-radius: 18px 18px 0 0; max-height: 92vh; padding-bottom: env(safe-area-inset-bottom, 0px); }
}
</style>
