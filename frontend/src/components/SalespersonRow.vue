<!-- Copyright (c) 2026 Lumen Solutions
     SPDX-License-Identifier: AGPL-3.0-only
     Lumen Restaurants: who served the order, on the restaurant order screen
     (LumenPOS 0.57.0 has the same row in the shop cart, CartPanel.vue). Shown
     while the outlet has salespeople and the setting is not Off, marked when
     Settings make it Required. On a table order it is kept with the order
     (stores/cart.js orderSnapshot), so whoever takes the money sees who served. -->
<template>
  <div
    v-if="session.salesPersons.length && session.settings.salesperson_mode !== 'Off'"
    class="sp-row"
    data-tour="cart-salesperson"
    :class="{ needed: required && !cart.salesPerson }"
  >
    <span class="muted small">{{ t('Salesperson') }}<template v-if="required"> *</template></span>
    <span v-if="cart.salesPerson" class="sp-chip">
      <bdi>{{ chosenLabel }}</bdi>
      <button class="chip-x" :title="t('Remove')" @click="cart.salesPerson = null"><Icon name="close" /></button>
    </span>
    <template v-else>
      <input v-model="query" list="sp-options-restaurant" :placeholder="t('Name or number…')" @change="pick" />
      <datalist id="sp-options-restaurant">
        <option v-for="sp in session.salesPersons" :key="sp.name" :value="label(sp)" />
      </datalist>
    </template>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import Icon from './Icon.vue'
import { t } from '../i18n'
import { useCartStore } from '../stores/cart'
import { useSessionStore } from '../stores/session'

const cart = useCartStore()
const session = useSessionStore()
const query = ref('')
const required = computed(() => session.settings.salesperson_mode === 'Required')

function label(sp) {
  return sp.sales_person_no ? `${sp.sales_person_name} #${sp.sales_person_no}` : sp.sales_person_name
}

const chosenLabel = computed(() => {
  const sp = session.salesPersons.find((s) => s.name === cart.salesPerson)
  return sp ? label(sp) : cart.salesPerson
})

// The typed text or the picked line of the list: the full label, the name or the number.
function pick() {
  const typed = query.value.trim().toLowerCase()
  if (!typed) return
  const found = session.salesPersons.find(
    (sp) =>
      label(sp).toLowerCase() === typed ||
      sp.sales_person_name.toLowerCase() === typed ||
      String(sp.sales_person_no || '').toLowerCase() === typed
  )
  if (found) {
    cart.salesPerson = found.name
    query.value = ''
  }
}
</script>

<style scoped>
.sp-row { display: flex; align-items: center; gap: 10px; padding: 8px 14px; border-bottom: 1px solid var(--border); }
.sp-row input { flex: 1; min-width: 0; padding: 7px 10px; border: 1px solid var(--border); border-radius: 9px; font: inherit; font-size: 13px; background: var(--surface); color: var(--text); }
.sp-row.needed input { border-color: var(--amber); }
.sp-chip { display: inline-flex; align-items: center; gap: 6px; padding: 4px 6px 4px 10px; border-radius: 999px; background: var(--surface-2); font-size: 13px; font-weight: 600; }
.chip-x { border: 0; background: transparent; color: var(--text-muted); cursor: pointer; display: inline-flex; padding: 2px; }
</style>
