<!-- Copyright (c) 2026 Lumen Solutions
     SPDX-License-Identifier: AGPL-3.0-only
     "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md. -->
<template>
  <div class="resv">
    <div class="card resv-card">
      <div class="resv-head">
        <div class="rh-title"><Icon name="clock" /> {{ t('Reservations') }}</div>
        <div class="rh-days">
          <button class="day-btn" :class="{ active: offset === 0 }" @click="setOffset(0)">{{ t('Today') }}</button>
          <button class="day-btn" :class="{ active: offset === 1 }" @click="setOffset(1)">{{ t('Tomorrow') }}</button>
          <input type="date" :value="date" @change="setDate($event.target.value)" />
        </div>
        <button v-if="session.permissions.booking_page?.write" class="btn btn-outline" @click="$router.push('/booking-designer')">
          <Icon name="image" /> {{ t('Booking page') }}
        </button>
        <button class="btn btn-primary" @click="startNew">+ {{ t('New reservation') }}</button>
      </div>

      <div class="resv-body">
        <!-- online requests wait for a person -->
        <div v-if="requested.length" class="tray">
          <div class="tray-title">
            <Icon name="bulb" /> {{ t('{n} online requests waiting', { n: requested.length }) }}
          </div>
          <div v-for="row in requested" :key="row.name" class="rrow request">
            <div class="rtime">
              <b>{{ row.reservation_time }}</b>
              <span class="muted small">{{ dayLabel(row.reservation_date) }}</span>
            </div>
            <div class="rwho">
              <b>{{ row.customer_name }}</b>
              <span class="muted small ltr">{{ row.phone }}</span>
              <span v-if="row.note" class="muted small">{{ row.note }}</span>
              <span v-for="a in row.answers || []" :key="a.key" class="muted small">{{ a.label }}: <b>{{ a.value === '1' ? t('Yes') : a.value }}</b></span>
              <span v-if="(row.items || []).length" class="pkgs">
                <span v-for="it in row.items" :key="it.item_code">{{ it.qty }} × {{ it.item_name }}</span>
                <b v-if="row.estimated_total">{{ money(row.estimated_total) }}</b>
              </span>
            </div>
            <span class="pill">{{ t('{n} guests', { n: row.guests }) }}</span>
            <div class="racts">
              <button class="btn btn-primary sm" @click="setStatus(row, 'Confirmed')">{{ t('Confirm') }}</button>
              <button class="btn btn-outline sm danger" @click="setStatus(row, 'Cancelled')">{{ t('Decline') }}</button>
            </div>
          </div>
        </div>

        <div v-if="session.offline" class="rempty muted">{{ t('Reservations need a connection.') }}</div>
        <div v-else-if="loading" class="rempty muted">{{ t('Loading…') }}</div>
        <div v-else-if="!rows.length" class="rempty muted">{{ t('Nothing booked for this day.') }}</div>

        <div v-for="row in rows" :key="row.name" class="rrow" :class="{ dim: isClosed(row) }">
          <div class="rtime"><b>{{ row.reservation_time }}</b></div>
          <div class="rwho">
            <b>{{ row.customer_name }}</b>
            <span class="muted small ltr">{{ row.phone }}</span>
            <span v-if="row.note" class="muted small">{{ row.note }}</span>
            <span v-for="a in row.answers || []" :key="a.key" class="muted small">{{ a.label }}: <b>{{ a.value === '1' ? t('Yes') : a.value }}</b></span>
            <span v-if="(row.items || []).length" class="pkgs">
              <span v-for="it in row.items" :key="it.item_code">{{ it.qty }} × {{ it.item_name }}</span>
              <b v-if="row.estimated_total">{{ money(row.estimated_total) }}</b>
            </span>
          </div>
          <span class="pill">{{ t('{n} guests', { n: row.guests }) }}</span>
          <span v-if="row.table_label" class="pill">{{ row.table_label }}</span>
          <span class="pill" :class="statusClass(row.status)">{{ t(row.status) }}</span>
          <div class="racts" v-if="row.status === 'Confirmed' || row.status === 'Requested'">
            <button class="btn btn-primary sm" @click="seat(row)">{{ t('Arrived') }}</button>
            <button class="btn btn-outline sm" @click="setStatus(row, 'No show')">{{ t('No show') }}</button>
            <button class="btn btn-outline sm" @click="edit(row)">{{ t('Edit') }}</button>
            <button class="btn btn-outline sm danger" @click="setStatus(row, 'Cancelled')">{{ t('Cancel') }}</button>
          </div>
        </div>
      </div>
    </div>

    <!-- new / edit -->
    <div v-if="form" class="modal-backdrop" @click.self="form = null">
      <div class="modal" style="width: 420px">
        <div class="modal-header">
          <Icon name="clock" /> {{ form.name ? t('Edit reservation') : t('New reservation') }}
          <button class="btn-ghost" @click="form = null"><Icon name="close" /></button>
        </div>
        <div class="modal-body form">
          <label class="field-label">{{ t('Name') }}</label>
          <input ref="nameInput" v-model="form.customer_name" />
          <label class="field-label">{{ t('Phone') }}</label>
          <input v-model="form.phone" type="tel" dir="ltr" placeholder="05xxxxxxxx" />
          <div class="two">
            <div>
              <label class="field-label">{{ t('Date') }}</label>
              <input type="date" v-model="form.reservation_date" />
            </div>
            <div>
              <label class="field-label">{{ t('Time') }}</label>
              <input type="time" v-model="form.reservation_time" />
            </div>
          </div>
          <div class="two">
            <div>
              <label class="field-label">{{ t('Guests') }}</label>
              <input type="number" min="1" v-model.number="form.guests" />
            </div>
            <div>
              <label class="field-label">{{ t('Table (optional)') }}</label>
              <select v-model="form.table">
                <option :value="null">{{ t('Pick on arrival') }}</option>
                <option v-for="table in tables" :key="table.name" :value="table.name">
                  {{ table.area }} {{ table.table_no }}
                </option>
              </select>
            </div>
          </div>
          <label class="field-label">{{ t('Note') }}</label>
          <input v-model="form.note" :placeholder="t('Occasion, high chair, by the window…')" />
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline" @click="form = null">{{ t('Cancel') }}</button>
          <button class="btn btn-primary" :disabled="busy" @click="save">
            {{ busy ? t('Saving…') : t('Save reservation') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import Icon from '../components/Icon.vue'
import { call } from '../api'
import { useSessionStore } from '../stores/session'
import { useCartStore } from '../stores/cart'
import { t } from '../i18n'
import { money } from '../format'

const router = useRouter()
const session = useSessionStore()
const cart = useCartStore()

const rows = ref([])
const requested = ref([])
const tables = ref([])
const loading = ref(true)
const busy = ref(false)
const offset = ref(0)
const date = ref(toDate(0))
const form = ref(null)
const nameInput = ref(null)
let poll = null

// The site's own today (and tomorrow), on the site's clock (LumenPOS 0.61.1's
// session.siteNow): the device's date read through toISOString was the UTC
// date, so in Riyadh between midnight and three "Today" was yesterday.
function toDate(days) {
  const d = new Date(session.siteNow())
  d.setUTCDate(d.getUTCDate() + days)
  return d.toISOString().slice(0, 10)
}

function setOffset(n) {
  offset.value = n
  date.value = toDate(n)
  load()
}

function setDate(value) {
  date.value = value
  offset.value = value === toDate(0) ? 0 : value === toDate(1) ? 1 : -1
  load()
}

function dayLabel(value) {
  if (value === toDate(0)) return t('Today')
  if (value === toDate(1)) return t('Tomorrow')
  return value
}

function isClosed(row) {
  return row.status === 'Cancelled' || row.status === 'No show' || row.status === 'Seated'
}

function statusClass(status) {
  return { ok: status === 'Confirmed' || status === 'Seated', warn: status === 'Requested', bad: status === 'Cancelled' || status === 'No show' }
}

async function load() {
  if (session.offline) {
    loading.value = false
    return
  }
  try {
    const data = await call('lumen_restaurants.api.reservations.day', {
      pos_profile: session.posProfile,
      date: date.value,
    })
    rows.value = data.rows || []
    requested.value = data.requested || []
  } catch (e) {
    session.notify(e.message, true)
  } finally {
    loading.value = false
  }
}

async function loadTables() {
  try {
    tables.value = (await call('lumen_restaurants.api.restaurant.list_tables', {
      pos_profile: session.posProfile,
    })).filter((x) => !x.disabled)
  } catch {
    tables.value = []
  }
}

function startNew() {
  form.value = {
    name: null,
    customer_name: '',
    phone: '',
    reservation_date: date.value,
    reservation_time: '19:00',
    guests: 2,
    table: null,
    note: '',
  }
  nextTick(() => nameInput.value?.focus())
}

function edit(row) {
  form.value = {
    name: row.name,
    customer_name: row.customer_name,
    phone: row.phone,
    reservation_date: date.value,
    reservation_time: row.reservation_time,
    guests: row.guests,
    table: row.table || null,
    note: row.note || '',
  }
}

async function save() {
  busy.value = true
  try {
    await call('lumen_restaurants.api.reservations.save_reservation', {
      payload: { ...form.value, pos_profile: session.posProfile },
    })
    form.value = null
    await load()
    session.notify(t('Reservation saved'))
  } catch (e) {
    session.notify(e.message, true)
  } finally {
    busy.value = false
  }
}

async function setStatus(row, status) {
  try {
    await call('lumen_restaurants.api.reservations.set_reservation_status', { name: row.name, status })
    await load()
  } catch (e) {
    session.notify(e.message, true)
  }
}

// Arrived: seat them. If the reservation named a free table, the order opens
// there and the till lands straight on it; otherwise go pick a table.
async function seat(row) {
  try {
    const res = await call('lumen_restaurants.api.reservations.set_reservation_status', { name: row.name, status: 'Seated' })
    if (res.order) {
      const order = await call('lumen_restaurants.api.restaurant.get_order', { name: res.order.name })
      await cart.openOrder(order)
      router.push('/')
    } else {
      router.push('/tables')
    }
  } catch (e) {
    session.notify(e.message, true)
  }
}

onMounted(() => {
  load()
  loadTables()
  poll = setInterval(load, 20000)
})
onUnmounted(() => clearInterval(poll))
</script>

<style scoped>
.resv { flex: 1; display: flex; padding: 14px; overflow: hidden; }
.resv-card { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.resv-head { display: flex; align-items: center; gap: 12px; padding: 12px 14px; border-bottom: 1px solid var(--border); flex-wrap: wrap; }
.rh-title { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 15px; }
.rh-days { display: flex; gap: 6px; align-items: center; margin-inline-start: auto; flex-wrap: wrap; min-width: 0; max-width: 100%; }
.day-btn { border: 1px solid var(--border); background: var(--card-bg); border-radius: 999px; padding: 8px 16px; font: inherit; font-size: 13px; font-weight: 600; color: var(--text-muted); cursor: pointer; }
.day-btn.active { background: var(--brand); border-color: var(--brand); color: #fff; }
.rh-days input { min-width: 0; max-width: 100%; padding: 7px 9px; border: 1px solid var(--border); border-radius: 10px; font: inherit; font-size: 13px; }
.resv-body { flex: 1; overflow: auto; padding: 14px; background: var(--page-bg); }
.tray { border: 1.5px dashed var(--brand-soft); background: rgba(20, 99, 255, 0.05); border-radius: 14px; padding: 10px 12px 4px; margin-bottom: 14px; }
.tray-title { display: flex; align-items: center; gap: 7px; font-size: 13px; font-weight: 700; color: var(--brand-dark); margin: 2px 2px 8px; }
.rrow {
  background: var(--card-bg); border: 1px solid var(--border); border-radius: 13px;
  padding: 12px 14px; margin-bottom: 9px; display: flex; align-items: center; gap: 14px; flex-wrap: wrap;
}
.rrow.dim { opacity: 0.55; }
.rrow.request { border-color: var(--brand-soft); }
.rtime { min-width: 62px; }
.rtime b { font-size: 16px; }
.rtime .small { display: block; }
.rwho { flex: 1; min-width: 160px; }
.rwho > b { display: block; font-size: 14px; }
.rwho .small { display: block; }
.ltr { direction: ltr; text-align: start; }
.pkgs { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 4px; }
.pkgs span { background: rgba(20, 99, 255, 0.08); color: var(--brand-dark); border-radius: 7px; padding: 1px 9px; font-size: 12px; font-weight: 600; }
.pkgs b { font-size: 12.5px; }
.pill { background: var(--surface-2); border-radius: 8px; padding: 3px 11px; font-size: 12.5px; white-space: nowrap; }
.pill.ok { background: rgba(20, 99, 255, 0.12); color: var(--brand-dark); font-weight: 700; }
.pill.warn { background: rgba(201, 130, 27, 0.15); color: var(--amber); font-weight: 700; }
.pill.bad { background: rgba(214, 69, 69, 0.12); color: var(--red); font-weight: 700; }
.racts { display: flex; gap: 7px; flex-wrap: wrap; }
.btn.sm { padding: 8px 14px; font-size: 12.5px; border-radius: 9px; }
.btn.danger { color: var(--red); }
.rempty { padding: 30px; text-align: center; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.two select, .two input { width: 100%; }
</style>
