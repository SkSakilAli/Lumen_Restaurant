<!-- Copyright (c) 2026 Lumen Solutions
     SPDX-License-Identifier: AGPL-3.0-only
     "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md. -->
<template>
  <div class="rsell">
    <!-- ======================= the order ======================= -->
    <aside class="rorder card">
      <div v-if="cart.order" class="rtable-strip">
        <div class="rt-where">
          <Icon name="table" />
          <strong>{{ cart.order.table_label || t(cart.order.order_type) }}</strong>
          <span v-if="cart.order.guests" class="muted small">&nbsp;· {{ cart.order.guests }} {{ t('guests') }}</span>
        </div>
        <button class="btn-ghost" :title="t('Save and go back to the tables')" @click="leaveOrder">
          <Icon name="check" /> {{ t('Save') }}
        </button>
      </div>
      <div v-else class="rtype" data-tour="order-type">
        <button :class="{ active: cart.serviceType === 'Dine in' }" @click="pickDineIn">
          {{ t('Dine in') }}
        </button>
        <button :class="{ active: cart.serviceType === 'Takeaway' }" @click="setType('Takeaway')">
          {{ t('Takeaway') }}
        </button>
        <button :class="{ active: cart.serviceType === 'Delivery' }" @click="setType('Delivery')">
          {{ t('Delivery') }}
        </button>
      </div>

      <div v-if="!cart.order" class="rnum-hint">
        <template v-if="cart.serviceType === 'Delivery'">
          <select :value="cart.appType || ''" @change="cart.setChannel($event.target.value || null)">
            <option value="">{{ t('Own delivery') }}</option>
            <option v-for="app in session.settings.delivery_apps" :key="app.app_name" :value="app.app_name">
              {{ app.app_name }}
            </option>
          </select>
          <input
            v-if="cart.appType"
            v-model="cart.orderId"
            :placeholder="cart.activeApp?.require_order_id ? t('Order ID *') : t('Order ID')"
          />
        </template>
        <span v-else class="muted small">{{ t('The order number prints with the payment') }}</span>
      </div>

      <div class="rcustomer" data-tour="cart-customer" role="button" tabindex="0" @click="customerOpen = true">
        <Icon name="person" />
        <span v-if="cart.customer">{{ cart.customer.customer_name }}</span>
        <span v-else class="muted">{{ t('Customer (optional)') }}</span>
        <button v-if="cart.customer" class="btn-ghost" @click.stop="cart.setCustomer(null)"><Icon name="close" /></button>
      </div>
      <!-- Lumen Restaurants: who served the order (LumenPOS 0.57.0's salesperson). -->
      <SalespersonRow />

      <div class="rlines" data-tour="cart-lines">
        <div v-if="!cart.lines.length" class="rempty muted">
          {{ t('Tap the menu to start the order') }}
        </div>
        <template v-for="(line, i) in cart.lines" :key="(line.lr_line || line.item_code) + '-' + i">
        <div v-if="!line.lr_addon_of" class="rline">
          <div class="rl-main">
            <div class="rl-name">
              <b>{{ line.item_name }}</b>
              <!-- Lumen Restaurants: the dish's free choices, then its paid lines. -->
              <span v-if="freeChoices(line).length" class="rl-choices">{{ freeChoices(line).join(listSep) }}</span>
              <span v-if="line.note" class="rl-note">{{ line.note }}</span>
              <span v-if="line.price_override != null" class="rl-typed">{{ t('Price changed at the till') }}</span>
              <span v-if="line.sent_qty" class="rl-sent"><Icon name="check" /> {{ t('sent {n}', { n: line.sent_qty }) }}</span>
            </div>
            <div class="rl-price">{{ money(line.price * line.qty) }}</div>
          </div>
          <div v-for="addon in addonsOf(cart, line.lr_line)" :key="addon.item_code" class="rl-addon">
            <span>+ {{ addon.item_name }}</span><span>{{ money(addon.price * addon.qty) }}</span>
          </div>
          <div class="rl-tools">
            <div class="stepper">
              <button @click="stepQty(i, line, -1)">-</button>
              <b>{{ line.qty }}</b>
              <button @click="stepQty(i, line, 1)">+</button>
            </div>
            <button v-if="groupsOf(line).length" class="rl-tool" @click="editDish(line)">
              {{ t('Add-ons') }}
            </button>
            <button class="rl-tool" :class="{ on: noteFor === i }" @click="noteFor = noteFor === i ? null : i; priceFor = null">
              {{ t('Note') }}
            </button>
            <!-- A price typed for the dish: the outlet allows it (POS Profile,
                 Allow User to Edit Rate) and the person may edit prices. -->
            <button v-if="canChangePrice" class="rl-tool" :class="{ on: priceFor === i }" @click="priceFor = priceFor === i ? null : i; noteFor = null">
              {{ t('Price') }}
            </button>
            <button class="rl-tool danger" @click="removeLine(i, line)"><Icon name="close" /></button>
          </div>
          <input
            v-if="noteFor === i"
            class="rl-note-input"
            :value="line.note || ''"
            :placeholder="t('No onions, well done, on the side…')"
            @change="cart.setLineNote(i, $event.target.value); noteFor = null"
            @keyup.enter="$event.target.blur()"
          />
          <div v-if="priceFor === i" class="rl-price-edit">
            <input
              class="rl-note-input rl-price-input"
              type="text"
              inputmode="decimal"
              :value="line.price_override != null ? String(line.price_override) : String(cart.inSale(line.price))"
              :placeholder="String(cart.inSale(line.price_before_override ?? line.price))"
              @change="typePrice(line, $event.target.value)"
              @keyup.enter="$event.target.blur()"
            />
            <span class="muted small">
              {{ linesOf(line.item_code) > 1
                ? t('One price for every {item} on this order', { item: line.item_name })
                : t('Leave it empty for the menu price') }}
            </span>
          </div>
        </div>
        </template>
      </div>

      <div class="rtotals" data-tour="cart-totals">
        <div class="rt-row" v-if="cart.taxBreakdown.exclusiveTotal > 0">
          <span>{{ t('Tax') }}</span><span>{{ money(cart.taxBreakdown.exclusiveTotal) }}</span>
        </div>
        <div class="rt-row" v-for="tax in cart.taxBreakdown.included" :key="tax.description">
          <span>{{ t('Includes {tax}', { tax: tax.description }) }}</span><span>{{ money(tax.amount) }}</span>
        </div>
        <div class="rt-row big"><span>{{ t('Total') }}</span><span>{{ money(cart.total) }}</span></div>
      </div>

      <div class="ractions">
        <button
          v-if="cart.order"
          class="btn btn-outline rfire"
          data-tour="kitchen-send"
          :disabled="firing || !unsentCount"
          @click="fire"
        >
          <Icon name="bulb" /> {{ firing ? t('Sending…') : unsentCount ? t('Send Order ({n})', { n: unsentCount }) : t('Order sent') }}
        </button>
        <button class="btn btn-primary rpay" data-tour="cart-pay" :disabled="!cart.lines.length || !session.registerOpen" @click="onPay">
          {{ t('Pay') }} · {{ money(cart.total) }}
        </button>
        <p v-if="!session.registerOpen" class="muted small center">{{ t('Open the register to take payments') }}</p>
      </div>
    </aside>

    <!-- ======================= the menu ======================= -->
    <main class="rmenu card">
      <div v-if="readyCalls.length" class="rready">
        <div class="rr-text">
          <Icon name="check" />
          <b>{{ t('Ready to hand over:') }}</b>
          <span v-for="call_ in readyCalls" :key="call_.name" class="rr-chip" :class="{ 'bar-chip': call_.station === 'Bar' }">
            <span v-if="call_.station === 'Bar'" style="margin-right: 4px;">🍸</span>{{ call_.order_no ? '#' + call_.order_no : call_.table_label }}
          </span>
        </div>
        <button class="btn btn-outline" @click="deliverFirst">{{ t('Handed over') }}</button>
      </div>

      <div class="rmenu-head">
        <div class="rsearch" data-tour="sell-search">
          <Icon name="search" />
          <input
            :value="catalog.search"
            :placeholder="t('Search the menu…')"
            @input="catalog.setSearch($event.target.value)"
          />
        </div>
      </div>

      <div class="rmenu-body">
        <div class="rcats" data-tour="sell-groups">
          <button class="rcat" :class="{ active: !catalog.itemGroup }" @click="catalog.setGroup('')">
            {{ t('All') }}
          </button>
          <button
            v-for="group in menuGroups"
            :key="group"
            class="rcat"
            :class="{ active: catalog.itemGroup === group }"
            @click="catalog.setGroup(group)"
          >
            {{ group }}
          </button>
        </div>
        <div class="rgrid" data-tour="sell-products">
          <button v-for="item in menuItems" :key="item.item_code" class="ritem" @click="add(item)">
            <span class="ri-ph" :style="phStyle(item)">
              <img v-if="item.image" :src="item.image" loading="lazy" />
              <template v-else>{{ initial(item) }}</template>
            </span>
            <b>{{ item.item_name }}</b>
            <span class="ri-price">{{ money(item.price) }}</span>
            <span v-if="groupsOf(item).length" class="ri-mods">{{ t('Has add-ons') }}</span>
          </button>
          <div v-if="!menuItems.length" class="rempty muted">{{ t('Nothing here yet') }}</div>
        </div>
      </div>
    </main>

    <ModifierSheet
      v-if="sheet"
      :item="sheet.item"
      :groups="sheet.groups"
      :initial-picks="sheet.picks"
      :initial-qty="sheet.qty"
      :initial-note="sheet.note"
      :editing="Boolean(sheet.lineId)"
      :locked="sheet.locked"
      @save="saveSheet"
      @remove="removeFromSheet"
      @close="sheet = null"
    />
    <CustomerModal v-if="customerOpen" @close="customerOpen = false" />
    <PaymentOverlay v-if="paymentOpen" @close="paymentOpen = false" @done="onSaleDone" />
    <ReceiptModal v-if="receipt" :receipt="receipt" @close="closeReceipt" />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import Icon from '../components/Icon.vue'
import CustomerModal from '../components/CustomerModal.vue'
import PaymentOverlay from '../components/PaymentOverlay.vue'
import ReceiptModal from '../components/ReceiptModal.vue'
import ModifierSheet from '../components/ModifierSheet.vue'
import SalespersonRow from '../components/SalespersonRow.vue'
import { useModifierStore } from '../stores/modifiers'
import {
  addDish, updateDish, setDishQty, removeDish, addonsOf, freeChoices, picksFrom, defaultPicks, missingGroups,
  setItemPrice,
} from '../addons'
import { call } from '../api'
import { useSessionStore } from '../stores/session'
import { useCatalogStore } from '../stores/catalog'
import { useCartStore } from '../stores/cart'
import { money } from '../format'
import { t, locale } from '../i18n'

const router = useRouter()
const session = useSessionStore()
const catalog = useCatalogStore()
const cart = useCartStore()
const modifiers = useModifierStore()

const customerOpen = ref(false)
const paymentOpen = ref(false)
const receipt = ref(null)
const noteFor = ref(null)
const priceFor = ref(null)
// Type a price on a dish: where the outlet allows it and the person may.
const canChangePrice = computed(() => Boolean(session.permissions?.can_change_price))
const firing = ref(false)
const readyCalls = ref([])
let readyTimer = null

// A paid add-on goes to the kitchen with its dish, it is not counted apart.
const unsentCount = computed(() =>
  cart.lines.reduce(
    (sum, line) => (line.lr_addon_of ? sum : sum + Math.max(0, line.qty - (line.sent_qty || 0))),
    0
  )
)

// --- Lumen Restaurants: add-ons -------------------------------------------
const sheet = ref(null)
const listSep = computed(() => (locale.value === 'ar' ? '، ' : ', '))
const menuItems = computed(() => catalog.items.filter((item) => !modifiers.isAddonItem(item)))
const menuGroups = computed(() => session.itemGroups.filter((group) => group !== modifiers.hiddenGroup))

function groupsOf(item) {
  return modifiers.groupsFor(item)
}

function openSheet(item, line = null) {
  const groups = groupsOf(item)
  sheet.value = {
    item: line ? { ...item, price: line.price } : item,
    groups,
    lineId: line?.lr_line || null,
    picks: line ? picksFrom(line) : defaultPicks(groups),
    qty: line ? line.qty : 1,
    note: line ? line.note || '' : '',
    // what the kitchen already has keeps its choices
    locked: Boolean(line && line.sent_qty),
  }
}

function editDish(line) {
  openSheet(line, line)
}

function saveSheet({ picks, qty, note }) {
  const s = sheet.value
  if (s.lineId) updateDish(cart, s.lineId, s.groups, picks, qty, note, modifiers.hiddenGroup)
  else addDish(cart, s.item, s.groups, picks, qty, note, modifiers.hiddenGroup)
  sheet.value = null
}

function removeFromSheet() {
  if (sheet.value?.lineId) removeDish(cart, sheet.value.lineId)
  sheet.value = null
}

// One price for the item on every line of it (addons.js setItemPrice).
function typePrice(line, value) {
  setItemPrice(cart, line.item_code, value)
  priceFor.value = null
}

function linesOf(itemCode) {
  return cart.lines.filter((l) => l.item_code === itemCode && !l.lr_addon_of && !l.bundle_key).length
}

function stepQty(i, line, step) {
  if (line.lr_line) setDishQty(cart, line.lr_line, line.qty + step)
  else cart.setQty(i, line.qty + step)
}

function removeLine(i, line) {
  if (line.lr_line) removeDish(cart, line.lr_line)
  else cart.removeLine(i)
}

function setType(type) {
  cart.serviceType = type
  if (type !== 'Delivery') cart.setChannel(null)
}

// "Dine in" on an empty screen means: go pick the table. The basket, if one
// was started, rides along and lands on the table the user opens.
function pickDineIn() {
  cart.serviceType = 'Dine in'
  router.push('/tables')
}

function initial(item) {
  return (item.item_name || '?').trim().charAt(0)
}

const PALETTE = ['#eaf1ff', '#fdf3e2', '#eef1f6', '#f3eafd', '#fdeaea', '#eef7fb']
function phStyle(item) {
  if (item.image) return {}
  let hash = 0
  for (const ch of item.item_code || '') hash = (hash * 31 + ch.charCodeAt(0)) % 997
  return { background: PALETTE[hash % PALETTE.length] }
}

function add(item) {
  if (item.has_serial_no) {
    return session.notify(t('Serialized items are sold from the retail screen'), true)
  }
  if (item.is_stock_item && !session.allowNegativeStock && !session.offline) {
    const inCart = cart.lines.find((l) => l.item_code === item.item_code)?.qty || 0
    if (inCart + 1 > (item.actual_qty || 0)) {
      return session.notify(t('{item}: only {qty} in stock', { item: item.item_name, qty: item.actual_qty || 0 }), true)
    }
  }
  const groups = groupsOf(item)
  if (groups.length && (modifiers.openOnTap || missingGroups(groups, defaultPicks(groups)).length)) {
    return openSheet(item)
  }
  addDish(cart, item, groups, defaultPicks(groups), 1, '', modifiers.hiddenGroup)
  if (groups.length) session.notify(t('Added. Tap its line for the add-ons.'))
}

// Put the table down and go back to the floor, saving first.
async function leaveOrder() {
  try {
    await cart.leaveOrder()
    router.push('/tables')
  } catch (e) {
    session.notify(e.message, true)
  }
}

async function fire() {
  firing.value = true
  try {
    const res = await cart.sendToKitchen()
    if (res && (res.count || res.kitchen_items || res.bar_items)) {
      if (res.bar_items && res.kitchen_items) {
        session.notify(t('Sent to Kitchen & Bar'))
      } else if (res.bar_items) {
        session.notify(t('Sent to the Bar'))
      } else {
        session.notify(t('Sent to the Kitchen'))
      }
    }
  } catch (e) {
    session.notify(e.message, true)
  } finally {
    firing.value = false
  }
}

const wasTableOrder = ref(false)
function onPay() {
  if (cart.serviceType === 'Delivery' && cart.appType && cart.activeApp?.require_order_id && !cart.orderId.trim()) {
    return session.notify(t('Enter the {channel} order ID first', { channel: cart.appType }), true)
  }
  // Where the restaurant made the salesperson required (the server refuses it too).
  if (session.settings.salesperson_mode === 'Required' && session.salesPersons.length && !cart.salesPerson) {
    return session.notify(t('Pick the salesperson first'), true)
  }
  wasTableOrder.value = Boolean(cart.order)
  paymentOpen.value = true
}

function onSaleDone(saleReceipt) {
  paymentOpen.value = false
  receipt.value = saleReceipt
  loadReady()
}

function closeReceipt() {
  receipt.value = null
  if (wasTableOrder.value) {
    wasTableOrder.value = false
    router.push('/tables')
  }
}

async function loadReady() {
  if (session.offline || !session.restaurantMode) return
  try {
    readyCalls.value = await call('lumen_restaurants.api.kitchen.ready_calls', {
      pos_profile: session.posProfile,
    })
  } catch {
    readyCalls.value = []
  }
}

async function deliverFirst() {
  const first = readyCalls.value[0]
  if (!first) return
  try {
    await call('lumen_restaurants.api.kitchen.set_ticket_status', { name: first.name, status: 'Done' })
    await loadReady()
  } catch (e) {
    session.notify(e.message, true)
  }
}

// The payment screen opens already knowing the payable (see SellView).
watch(
  () => [cart.lines.length, cart.itemCount, cart.customer?.name, cart.couponCodes.length, cart.orderDiscountPercent],
  () => cart.prefetchQuote()
)

// While a table order is open, every change is saved back to it, debounced.
cart.$subscribe(() => cart.touchOrder())

onMounted(() => {
  catalog.fetch()
  modifiers.load()
  loadReady()
  readyTimer = setInterval(loadReady, 8000)
})
onUnmounted(() => clearInterval(readyTimer))
</script>

<style scoped>
.rsell { flex: 1; display: flex; gap: 14px; padding: 14px; overflow: hidden; }
.rorder { width: 360px; flex: none; display: flex; flex-direction: column; overflow: hidden; }
.rtable-strip {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  padding: 11px 14px; background: rgba(20, 99, 255, 0.08); border-bottom: 1px solid var(--border);
}
.rt-where { display: flex; align-items: center; gap: 7px; font-size: 14px; }
.rtype { display: flex; gap: 6px; padding: 12px 12px 0; }
.rtype button {
  flex: 1; border: 1.5px solid var(--border); background: var(--card-bg); border-radius: 11px;
  padding: 11px 4px; font: inherit; font-size: 13.5px; font-weight: 600; color: var(--text-muted); cursor: pointer;
}
.rtype button.active { background: var(--brand); border-color: var(--brand); color: #fff; }
.rnum-hint { display: flex; gap: 8px; align-items: center; padding: 9px 14px 0; }
.rnum-hint select, .rnum-hint input {
  flex: 1; min-width: 0; padding: 8px 10px; border: 1px solid var(--border); border-radius: 9px; font: inherit; font-size: 13px;
}
.rcustomer {
  display: flex; align-items: center; gap: 8px; margin: 10px 12px 0; padding: 9px 12px;
  border: 1px dashed var(--border); border-radius: 11px; font-size: 13px; cursor: pointer;
}
.rcustomer .btn-ghost { margin-inline-start: auto; }
.rlines { flex: 1; overflow: auto; padding: 6px 12px; }
.rempty { padding: 26px 10px; text-align: center; }
.rline { border-bottom: 1px solid var(--border-subtle); padding: 9px 0; }
.rl-main { display: flex; justify-content: space-between; gap: 10px; align-items: flex-start; }
.rl-name b { font-size: 14px; display: block; }
.rl-note { display: inline-block; background: var(--amber-soft, #fdf3e2); color: #9a6a0a; border-radius: 6px; padding: 0 8px; font-size: 11.5px; margin-top: 3px; }
.rl-sent { display: inline-flex; align-items: center; gap: 3px; color: var(--brand); font-size: 11.5px; margin-inline-start: 6px; }
.rl-price { font-weight: 700; font-size: 14px; white-space: nowrap; }
.rl-choices { display: block; color: var(--text-muted); font-size: 12px; margin-top: 2px; }
.rl-addon { display: flex; justify-content: space-between; gap: 10px; font-size: 12.5px; color: var(--brand-dark); font-weight: 600; margin-top: 3px; }
.ri-mods { font-size: 11px; font-weight: 700; color: var(--brand-dark); }
.rl-tools { display: flex; align-items: center; gap: 8px; margin-top: 7px; }
.stepper { display: flex; align-items: center; gap: 2px; border: 1.5px solid var(--border); border-radius: 10px; overflow: hidden; }
.stepper button { width: 34px; height: 32px; border: 0; background: transparent; font-size: 18px; font-weight: 600; cursor: pointer; color: var(--text); }
.stepper b { min-width: 28px; text-align: center; font-size: 14px; }
.rl-tool { border: 0; background: var(--surface-2); border-radius: 9px; padding: 7px 12px; font: inherit; font-size: 12px; font-weight: 600; color: var(--text-muted); cursor: pointer; }
.rl-tool.on { background: var(--brand); color: #fff; }
.rl-tool.danger { margin-inline-start: auto; color: var(--red); background: transparent; }
.rl-note-input { width: 100%; margin-top: 7px; padding: 8px 10px; border: 1px solid var(--border); border-radius: 9px; font: inherit; font-size: 13px; }
.rl-typed { display: block; color: var(--brand); font-size: 11.5px; margin-top: 2px; }
.rl-price-edit { display: flex; flex-direction: column; gap: 4px; }
.rl-price-input { max-width: 180px; font-variant-numeric: tabular-nums; }
.rtotals { border-top: 1px solid var(--border); padding: 10px 16px 2px; font-size: 13px; }
.rt-row { display: flex; justify-content: space-between; margin: 3px 0; color: var(--text-muted); }
.rt-row.big { color: var(--text); font-weight: 700; font-size: 17px; }
.ractions { padding: 10px 12px 14px; display: flex; flex-direction: column; gap: 8px; }
.rfire { width: 100%; }
.rpay { width: 100%; padding: 15px; font-size: 16.5px; border-radius: 13px; }
.center { text-align: center; margin: 0; }

.rmenu { flex: 1; min-width: 0; display: flex; flex-direction: column; overflow: hidden; }
.rready {
  display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap;
  margin: 12px 12px 0; padding: 10px 14px; background: rgba(20, 99, 255, 0.08);
  border: 1px solid rgba(20, 99, 255, 0.35); border-radius: 12px;
}
.rr-text { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; color: var(--brand-dark); font-size: 13.5px; }
.rr-chip { background: var(--card-bg); color: var(--text); border-radius: 8px; padding: 2px 12px; font-weight: 700; font-size: 15px; }
.rmenu-head { padding: 12px 12px 0; }
.rsearch { display: flex; align-items: center; gap: 7px; border: 1px solid var(--border); border-radius: 11px; padding: 0 12px; }
.rsearch .icon { color: var(--text-muted); }
.rsearch input { flex: 1; min-width: 0; width: 100%; border: 0; background: transparent; padding: 10px 0; font: inherit; font-size: 14px; outline: none; }
.rmenu-body { flex: 1; display: flex; min-height: 0; }
.rcats { width: 108px; flex: none; overflow: auto; padding: 12px 8px; display: flex; flex-direction: column; gap: 6px; border-inline-end: 1px solid var(--border-subtle); }
.rcat {
  border: 0; background: transparent; border-radius: 11px; padding: 10px 6px; font: inherit;
  font-size: 12.5px; font-weight: 600; color: var(--text-muted); cursor: pointer; text-align: center; word-break: break-word;
}
.rcat.active { background: rgba(20, 99, 255, 0.1); color: var(--brand-dark); }
.rgrid {
  flex: 1; overflow: auto; padding: 12px; display: grid; align-content: start;
  grid-template-columns: repeat(auto-fill, minmax(128px, 1fr)); gap: 10px; background: var(--page-bg);
}
.ritem {
  border: 1px solid var(--border); background: var(--card-bg); border-radius: 14px; padding: 10px;
  font: inherit; cursor: pointer; text-align: center; display: flex; flex-direction: column; gap: 6px;
}
.ritem:active { transform: scale(0.98); }
.ri-ph { height: 58px; border-radius: 10px; display: grid; place-items: center; font-size: 24px; font-weight: 700; color: var(--brand-dark); overflow: hidden; }
.ri-ph img { width: 100%; height: 100%; object-fit: cover; border-radius: 10px; }
.ritem b { font-size: 13px; line-height: 1.35; min-height: 35px; }
.ri-price { color: var(--brand); font-weight: 700; font-size: 13px; }

@media (max-width: 900px) {
  .rsell { flex-direction: column; overflow: auto; }
  .rorder { width: 100%; order: 2; }
  .rcats { width: 92px; }
}
</style>
