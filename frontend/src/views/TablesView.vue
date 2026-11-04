<!-- Copyright (c) 2026 Lumen Solutions
     SPDX-License-Identifier: AGPL-3.0-only
     "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
     Lumen Restaurants 0.1.0-r14: the Tables screen as a floor plan, built from
     the mockup "مخطط الصالة" the owner approved on 2026-10-01. Each area is a
     tab with its tables drawn where they stand; a tap on a table opens its
     panel; move and merge are picked on the plan; the list stays available
     (and is the only view where the outlet switches the plan off). Whoever
     may edit the plan draws it here (permission "Edit the floor plan"). -->
<template>
  <div class="floor" :class="{ picking: Boolean(pick) }">
    <div class="floor-card">
      <div class="floor-head">
        <div class="tabs" role="tablist">
          <button
            v-if="!showPlan"
            type="button"
            class="tab"
            role="tab"
            :aria-selected="String(areaSel === 'all')"
            @click="setArea('all')"
          >
            {{ t('All') }}<span class="count">{{ countText(null) }}</span>
          </button>
          <button
            v-for="a in areaList"
            :key="a.key"
            type="button"
            class="tab"
            role="tab"
            :aria-selected="String(areaSel === a.key)"
            @click="setArea(a.key)"
          >
            {{ areaLabel(a) }}<span v-if="!editing" class="count">{{ countText(a.key) }}</span>
          </button>
        </div>
        <div class="head-actions">
          <template v-if="editing">
            <div class="menu-wrap">
              <button
                type="button"
                class="btn btn-outline"
                :aria-expanded="String(menu === 'table')"
                @click.stop="menu = menu === 'table' ? null : 'table'"
              >
                <FloorIcon name="plus" /><span class="lbl">{{ t('Add a table') }}</span><FloorIcon name="chev" />
              </button>
              <div v-if="menu === 'table'" class="menu" role="menu" @click.stop>
                <button v-for="sh in SHAPES" :key="sh" type="button" role="menuitem" @click="addTable(sh)">
                  <FloorIcon :name="sh" art />{{ shapeLabel(sh) }}
                </button>
              </div>
            </div>
            <div class="menu-wrap">
              <button
                type="button"
                class="btn btn-outline"
                :aria-expanded="String(menu === 'item')"
                @click.stop="menu = menu === 'item' ? null : 'item'"
              >
                <FloorIcon name="plus" /><span class="lbl">{{ t('Add an item') }}</span><FloorIcon name="chev" />
              </button>
              <div v-if="menu === 'item'" class="menu" role="menu" @click.stop>
                <button v-for="k in KINDS" :key="k" type="button" role="menuitem" @click="addFx(k)">
                  <FloorIcon :name="k" art />{{ kindLabel(k) }}
                </button>
              </div>
            </div>
            <button type="button" class="btn btn-outline" :aria-label="t('Plan photo')" @click="openEditPanel('photo')">
              <FloorIcon name="image" /><span class="lbl">{{ t('Plan photo') }}</span>
            </button>
            <button type="button" class="btn btn-outline" :aria-label="t('New area')" @click="openEditPanel('area')">
              <FloorIcon name="layers" /><span class="lbl">{{ t('New area') }}</span>
            </button>
            <span class="sep"></span>
            <button type="button" class="btn btn-outline" :disabled="saving" @click="cancelEdit">{{ t('Cancel') }}</button>
            <button type="button" class="btn btn-primary" :disabled="saving" @click="saveEdit">
              <FloorIcon name="check" />{{ saving ? t('Saving…') : t('Save the plan') }}
            </button>
          </template>
          <template v-else>
            <div v-if="data.plan.on" class="seg" role="group" :aria-label="t('View')">
              <button type="button" :aria-pressed="String(view === 'plan')" @click="setView('plan')">
                <FloorIcon name="plan" />{{ t('Plan') }}
              </button>
              <button type="button" :aria-pressed="String(view === 'list')" @click="setView('list')">
                <FloorIcon name="list" />{{ t('List') }}
              </button>
            </div>
            <button
              v-if="canOpen"
              type="button"
              class="btn btn-outline"
              :aria-label="t('Takeaway')"
              :disabled="busy || session.offline"
              @click="newTakeaway"
            >
              <FloorIcon name="bag" /><span class="lbl">{{ t('Takeaway') }}</span>
            </button>
            <button
              v-if="data.plan.can_edit && !session.offline"
              type="button"
              class="btn btn-outline"
              :aria-label="t('Edit the plan')"
              @click="startEdit"
            >
              <FloorIcon name="edit" /><span class="lbl">{{ t('Edit the plan') }}</span>
            </button>
          </template>
        </div>
      </div>

      <div v-if="editing" class="plan-note">
        <FloorIcon name="edit" />
        <span class="grow">{{ t('Edit mode: drag a table or an item to move it, tap it to change it.') }}</span>
      </div>
      <div v-else-if="pick && pickFrom" class="plan-note">
        <FloorIcon :name="pick.kind" />
        <span class="grow">{{
          pick.kind === 'move'
            ? t('Tap a free table to move the order of {table} there', { table: tableLabel(pickFrom) })
            : t('Tap the table the order of {table} merges into', { table: tableLabel(pickFrom) })
        }}</span>
        <button v-if="pick.kind === 'move'" type="button" class="btn btn-outline btn-sm" :disabled="busy" @click="moveOffFloor">
          {{ t('Off the floor (takeaway counter)') }}
        </button>
        <button type="button" class="btn btn-outline btn-sm" @click="pick = null">{{ t('Cancel') }}</button>
      </div>

      <div v-if="session.offline" class="empty">
        {{ t('Tables need a connection: the order is shared between every device in the place.') }}
      </div>
      <div v-else-if="loading" class="empty">{{ t('Loading…') }}</div>
      <div v-else-if="!editing && !hasTables && !data.loose.length" class="empty">
        <span>{{
          data.plan.can_edit
            ? t('No tables yet. Tap Edit the plan to draw the floor and add the tables.')
            : t('No tables yet. Add them under Settings, General, Restaurant.')
        }}</span>
      </div>
      <div v-else-if="showPlan && planArea" class="plan-wrap">
        <FloorPlan
          :area="planArea"
          :tables="planTables"
          :editing="editing"
          :picking="Boolean(pick)"
          :selected-fx="sel && sel.kind === 'fx' ? sel.key : null"
          :label="t('Plan of {name}', { name: areaLabel(planArea) })"
          :rtl="isRTL()"
          @tap="tapTable"
          @pick="pickItem"
          @drag="dragItem"
          @blank="blank"
        />
      </div>
      <div v-else class="plan-wrap list-mode">
        <div class="list" :class="{ 'picking-list': Boolean(pick) }">
          <section v-for="sec in listSections" :key="sec.key" class="list-sec">
            <h3 v-if="areaSel === 'all'">{{ sec.label }}</h3>
            <div class="cards">
              <button
                v-for="tb in sec.tables"
                :key="tb.name"
                type="button"
                class="t-card"
                :class="['s-' + statusOf(tb), { selected: selected === tb.name, eligible: eligible(tb) }]"
                @click="tapTable(tb.name)"
              >
                <div class="c-head">
                  <span class="c-no">{{ tb.table_no }}</span>
                  <span class="chip sm" :class="'s-' + statusOf(tb)">{{ statusLabel(statusOf(tb)) }}</span>
                </div>
                <template v-if="tb.order">
                  <div class="c-amt">{{ money(tb.order.total) }}</div>
                  <div class="c-meta">{{ sinceText(tb.order.opened_at) }} · {{ t('{n} guests', { n: tb.order.guests || 0 }) }}</div>
                </template>
                <template v-else-if="tb.booking">
                  <div class="c-amt">{{ clockOf(tb.booking.time, t) }}</div>
                  <div class="c-meta">{{ t('{n} guests', { n: tb.booking.guests }) }}</div>
                </template>
                <div v-else class="c-meta end">{{ t('{n} seats', { n: tb.seats }) }}</div>
              </button>
            </div>
          </section>
        </div>
      </div>

      <div class="floor-foot">
        <div class="legend">
          <span v-for="k in LEGEND" :key="k" class="lg">
            <span class="sw" :class="'s-' + k"></span>{{ statusLabel(k) }} <b>{{ legend[k] }}</b>
          </span>
          <span class="lg"><FloorIcon name="person" />{{ legendGuests }} <b>{{ legend.guests }}</b></span>
        </div>
        <div v-if="data.loose.length && !editing" class="loose">
          <span>{{ t('Not at a table') }}</span>
          <button v-for="o in data.loose" :key="o.name" type="button" class="loose-chip" @click="openOrder(o.name)">
            <FloorIcon :name="o.order_type === 'Delivery' ? 'scooter' : 'bag'" />{{ t(o.order_type) }} · {{ money(o.total) }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="panelOpen && !editing" class="p-backdrop" @click="closePanel"></div>
    <aside class="panel" :class="{ open: panelOpen }">
      <!-- Edit mode: what is picked on the plan, or the area itself. -->
      <template v-if="editing && editArea">
        <template v-if="editPanel === 'photo'">
          <div class="p-head">
            <span class="p-title">{{ t('Plan photo') }}</span><span class="grow"></span>
            <button type="button" class="btn btn-ghost icon-btn" :aria-label="t('Close')" @click="editPanel = 'props'">
              <FloorIcon name="close" />
            </button>
          </div>
          <div class="p-body">
            <p class="hint">{{ t('Upload a photo or drawing of your real floor, then place the tables over it. It is only a guide for arranging.') }}</p>
            <label class="btn btn-outline btn-block" :class="{ 'is-busy': photoBusy }">
              <FloorIcon name="image" />{{ photoBusy ? t('Uploading…') : t('Choose a photo') }}
              <input type="file" accept="image/*" hidden :disabled="photoBusy" @change="choosePhoto" />
            </label>
            <template v-if="editArea.photo">
              <label class="field">
                <span class="field-label">{{ t('Photo strength') }}<output>{{ editArea.photo_opacity }}%</output></span>
                <input v-model.number="editArea.photo_opacity" type="range" min="10" max="100" step="5" />
              </label>
              <button type="button" class="btn btn-outline btn-danger-text btn-block" @click="editArea.photo = null">
                <FloorIcon name="trash" />{{ t('Remove the photo') }}
              </button>
            </template>
          </div>
        </template>

        <template v-else-if="editPanel === 'area'">
          <div class="p-head">
            <span class="p-title">{{ t('New area') }}</span><span class="grow"></span>
            <button type="button" class="btn btn-ghost icon-btn" :aria-label="t('Close')" @click="editPanel = 'props'">
              <FloorIcon name="close" />
            </button>
          </div>
          <div class="p-body">
            <label class="field">
              <span class="field-label">{{ t('Area name') }}</span>
              <input
                ref="areaNameInput"
                v-model="areaDraft"
                class="input"
                :placeholder="t('For example: First floor')"
                autocomplete="off"
                @keyup.enter="addArea"
              />
            </label>
          </div>
          <div class="p-foot">
            <button type="button" class="btn btn-primary btn-block" @click="addArea">
              <FloorIcon name="plus" />{{ t('Add the area') }}
            </button>
          </div>
        </template>

        <template v-else-if="selTableDraft">
          <div class="p-head">
            <span class="p-title">{{ t('Table {no}', { no: selTableDraft.table_no }) }}</span><span class="grow"></span>
            <button type="button" class="btn btn-ghost icon-btn" :aria-label="t('Close')" @click="deselect">
              <FloorIcon name="close" />
            </button>
          </div>
          <div class="p-body">
            <label class="field">
              <span class="field-label">{{ t('Table number') }}</span>
              <input v-model="selTableDraft.table_no" class="input" inputmode="numeric" autocomplete="off" @change="fixNumber" />
              <span v-if="isDup(selTableDraft)" class="hint err">{{ t('Another table already has this number') }}</span>
            </label>
            <div class="field">
              <span class="field-label">{{ t('Shape') }}</span>
              <div class="shape-grid">
                <button
                  v-for="sh in SHAPES"
                  :key="sh"
                  type="button"
                  class="shape-btn"
                  :aria-pressed="String(selTableDraft.shape === sh)"
                  @click="setShape(sh)"
                >
                  <FloorIcon :name="sh" art /><span>{{ shapeLabel(sh) }}</span>
                </button>
              </div>
            </div>
            <div class="field">
              <span class="field-label">{{ t('Seats') }}</span>
              <div class="stepper">
                <button type="button" class="btn btn-outline icon-btn" aria-label="-1" @click="addSeats(-1)"><FloorIcon name="minus" /></button>
                <output>{{ selTableDraft.seats }}</output>
                <button type="button" class="btn btn-outline icon-btn" aria-label="+1" @click="addSeats(1)"><FloorIcon name="plus" /></button>
              </div>
            </div>
            <div class="field">
              <span class="field-label">{{ t('Rotation') }}</span>
              <div class="stepper">
                <button type="button" class="btn btn-outline" :aria-label="t('Rotate counterclockwise')" @click="rotate(-15)">
                  <FloorIcon name="rotL" />15°
                </button>
                <output>{{ selTableDraft.rot }}°</output>
                <button type="button" class="btn btn-outline" :aria-label="t('Rotate clockwise')" @click="rotate(15)">
                  <FloorIcon name="rotR" />15°
                </button>
              </div>
            </div>
            <label class="field">
              <span class="field-label">{{ t('Area') }}</span>
              <select class="input" :value="selTableDraft.areaKey" @change="moveToArea($event.target.value)">
                <option v-for="a in draft.areas" :key="a.key" :value="a.key">{{ areaLabel(a) }}</option>
              </select>
            </label>
            <div class="setting-list">
              <label class="setting-row">
                <input type="checkbox" class="setting-toggle" :checked="selTableDraft.disabled" @change="setOff($event)" />
                <span class="setting-text">
                  <span class="setting-title">{{ t('Out of service') }}</span>
                  <span class="setting-desc">{{ t('A table that is out of service keeps its history and disappears from the floor screen.') }}</span>
                </span>
              </label>
            </div>
          </div>
          <div class="p-foot">
            <template v-if="confirmDelete">
              <p class="hint">{{ t('Remove this table?') }}</p>
              <div class="row-2">
                <button type="button" class="btn btn-danger" @click="deleteTable"><FloorIcon name="trash" />{{ t('Delete') }}</button>
                <button type="button" class="btn btn-outline" @click="confirmDelete = false">{{ t('Cancel') }}</button>
              </div>
            </template>
            <button v-else type="button" class="btn btn-outline btn-danger-text btn-block" @click="askDelete">
              <FloorIcon name="trash" />{{ t('Delete the table') }}
            </button>
          </div>
        </template>

        <template v-else-if="selFxDraft">
          <div class="p-head">
            <span class="p-title">{{ kindLabel(selFxDraft.kind) }}</span><span class="grow"></span>
            <button type="button" class="btn btn-ghost icon-btn" :aria-label="t('Close')" @click="deselect">
              <FloorIcon name="close" />
            </button>
          </div>
          <div class="p-body">
            <div v-if="selFxDraft.kind !== 'plant'" class="field">
              <span class="field-label">{{ t('Rotation') }}</span>
              <div class="stepper">
                <button type="button" class="btn btn-outline" :aria-label="t('Rotate counterclockwise')" @click="rotate(-15)">
                  <FloorIcon name="rotL" />15°
                </button>
                <output>{{ selFxDraft.rot }}°</output>
                <button type="button" class="btn btn-outline" :aria-label="t('Rotate clockwise')" @click="rotate(15)">
                  <FloorIcon name="rotR" />15°
                </button>
              </div>
            </div>
            <template v-if="BOXES.has(selFxDraft.kind)">
              <label class="field">
                <span class="field-label">{{ t('Width') }}<output>{{ selFxDraft.w }}</output></span>
                <input v-model.number="selFxDraft.w" type="range" min="40" max="400" step="10" />
              </label>
              <label class="field">
                <span class="field-label">{{ t('Depth') }}<output>{{ selFxDraft.h }}</output></span>
                <input v-model.number="selFxDraft.h" type="range" min="30" max="300" step="10" />
              </label>
            </template>
            <label v-else-if="selFxDraft.kind !== 'plant'" class="field">
              <span class="field-label">{{ t('Length') }}<output>{{ selFxDraft.w }}</output></span>
              <input v-model.number="selFxDraft.w" type="range" min="40" max="950" step="10" />
            </label>
            <label v-if="selFxDraft.kind === 'door'" class="field">
              <span class="field-label">{{ t('Name on the plan') }}</span>
              <input v-model="selFxDraft.label" class="input" maxlength="60" :placeholder="t('For example: Entrance')" autocomplete="off" />
            </label>
            <p v-if="selFxDraft.kind === 'plant'" class="hint">
              {{ t('Edit mode: drag a table or an item to move it, tap it to change it.') }}
            </p>
          </div>
          <div class="p-foot">
            <button type="button" class="btn btn-outline btn-danger-text btn-block" @click="deleteFx">
              <FloorIcon name="trash" />{{ t('Delete the item') }}
            </button>
          </div>
        </template>

        <template v-else>
          <div class="p-head"><span class="p-title">{{ areaLabel(editArea) }}</span></div>
          <div class="p-body">
            <label class="field">
              <span class="field-label">{{ t('Area name') }}</span>
              <input v-model="editArea.area_name" class="input" maxlength="140" autocomplete="off" />
            </label>
            <div class="meta one">
              <div><small>{{ t('Tables in this area') }}</small><b>{{ draftTablesIn(editArea.key).length }}</b></div>
            </div>
            <p class="hint">{{ t('Tap a table or an item to change it, or add a table from the top.') }}</p>
            <div class="row-2">
              <button type="button" class="btn btn-outline" @click="openEditPanel('photo')"><FloorIcon name="image" />{{ t('Plan photo') }}</button>
              <button type="button" class="btn btn-outline" @click="openEditPanel('area')"><FloorIcon name="layers" />{{ t('New area') }}</button>
            </div>
            <button
              v-if="draft.areas.length > 1 && !draftTablesIn(editArea.key).length"
              type="button"
              class="btn btn-outline btn-danger-text btn-block"
              @click="deleteArea"
            >
              <FloorIcon name="trash" />{{ t('Delete the area') }}
            </button>
          </div>
        </template>
      </template>

      <TablePanel
        v-else-if="selTable"
        v-model:guests="guestsDraft"
        v-model:note="noteDraft"
        v-model:reason="cancelReason"
        :table="selTable"
        :status="statusOf(selTable)"
        :status-label="statusLabel(statusOf(selTable))"
        :area-label="areaLabel(areaOfTable(selTable))"
        :sitting="selTable.order ? sinceText(selTable.order.opened_at) : ''"
        :bill="bill"
        :bill-loading="billLoading"
        :mode="panelMode"
        :busy="busy"
        :perms="perms"
        @close="closePanel"
        @start="startOrder"
        @seated="seat"
        @open="openOrder(selTable.order.name)"
        @pay="payTable"
        @print="printBill"
        @move="startPick('move')"
        @merge="startPick('merge')"
        @cancel-start="panelMode = 'cancel'"
        @cancel-confirm="cancelOrder"
        @back="panelMode = 'table'"
      />
      <NowPanel v-else :stats="nowStats" :upcoming="upcomingRows" @goto="gotoBooking" />
    </aside>
  </div>
  <!-- Outside .floor: the floor's own button sizes must not reach them. -->
  <PaymentOverlay v-if="paymentOpen" @close="closePayment" @done="onPaid" />
  <ReceiptModal v-if="receipt" :receipt="receipt" @close="closeReceipt" />
  <Teleport to="body">
    <div v-if="billToPrint" class="bill-print-host"><ReceiptView :receipt="billToPrint" printable /></div>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import '../floor/floor.css'
import FloorIcon from '../floor/FloorIcon.vue'
import FloorPlan from '../floor/FloorPlan.vue'
import NowPanel from '../floor/NowPanel.vue'
import TablePanel from '../floor/TablePanel.vue'
import {
  BOXES,
  FX_NEW,
  KINDS,
  NEW_SEATS,
  SEAT_RANGE,
  SHAPES,
  autoPlace,
  byNumber,
  clamp,
  clockOf,
  newKey,
  norm,
  roomWalls,
} from '../floor/plan'
import PaymentOverlay from '../components/PaymentOverlay.vue'
import ReceiptModal from '../components/ReceiptModal.vue'
import ReceiptView from '../components/ReceiptView.vue'
import { call } from '../api'
import { useCartStore } from '../stores/cart'
import { useSessionStore } from '../stores/session'
import { money } from '../format'
import { isRTL, t } from '../i18n'

const router = useRouter()
const session = useSessionStore()
const cart = useCartStore()

const LEGEND = ['free', 'busy', 'bill', 'book']
const SHAPE_LABEL = { round: 'Round', square: 'floor:Square', rect: 'Rectangle', booth: 'Booth' }
const KIND_LABEL = {
  wall: 'Wall',
  door: 'Door',
  window: 'Window',
  fence: 'Fence',
  plant: 'Plant',
  cashier: 'Cashier',
  kitchen: 'Kitchen',
  wc: 'Restrooms',
  sink: 'Hand wash',
}
const STATUS_LABEL = { free: 'floor:Free', busy: 'Occupied', bill: 'Bill requested', book: 'Booked', off: 'Out of service' }
const shapeLabel = (sh) => t(SHAPE_LABEL[sh])
const kindLabel = (k) => t(KIND_LABEL[k])
const statusLabel = (st) => t(STATUS_LABEL[st])

// ---- the floor, as the server last sent it ----------------------------------
const data = reactive({ tables: [], off: [], loose: [], areas: [], upcoming: [], plan: { on: true, can_edit: false } })
const loading = ref(true)
const busy = ref(false)
const phone = window.matchMedia?.('(max-width: 760px)').matches
const view = ref(phone ? 'list' : 'plan')
const areaSel = ref(null)
const selected = ref(null) // a table's name
const panelMode = ref('table')
const pick = ref(null) // { kind: 'move' | 'merge', from: table name }
const bill = ref(null)
const billLoading = ref(false)
let billFor = ''
const guestsDraft = ref(2)
const noteDraft = ref('')
const cancelReason = ref('')
// The server's clock, so a tablet set to the wrong time still shows the right
// "sitting for".
let clockSkew = 0
const now = ref(Date.now())
let ticker = null
let poll = null

const perms = computed(() => ({
  sell: session.permissions.sell !== false,
  open: session.permissions.can_open_table !== false,
  move: session.permissions.can_move_tables !== false,
  cancel: session.permissions.can_cancel_order !== false,
}))
const canOpen = computed(() => perms.value.open)

// Frappe sends "2026-09-23 13:29:18.130238", which is neither ISO nor UTC. Make
// it something Date can read; the skew below cancels the time zone out, because
// both sides are read the same way.
function serverTime(value) {
  if (!value) return 0
  return new Date(String(value).replace(' ', 'T').split('.')[0] + 'Z').getTime()
}
function minutesSince(opened) {
  if (!opened) return 0
  return Math.max(0, Math.floor((now.value - clockSkew - serverTime(opened)) / 60000))
}
function dur(mins) {
  if (mins < 60) return t('{n}m', { n: mins })
  return t('{h}h {m}m', { h: Math.floor(mins / 60), m: mins % 60 })
}
const sinceText = (opened) => dur(minutesSince(opened))

const sameName = (a, b) => (a || '').trim().toLowerCase() === (b || '').trim().toLowerCase()
function areaLabel(a) {
  if (!a) return ''
  return (a.area_name || '').trim() || t('Main hall')
}
function toTable(row) {
  return {
    name: row.name,
    key: row.name,
    table_no: row.table_no,
    area: row.area || '',
    seats: row.seats || 0,
    shape: row.shape || 'square',
    x: row.pos_x || 0,
    y: row.pos_y || 0,
    rot: row.rotation || 0,
    disabled: Boolean(row.disabled),
    order: row.order || null,
    booking: row.booking || null,
  }
}

function applyFloor(res) {
  const areas = (res.areas || []).map((a) => ({
    key: a.name || `v:${a.area_name}`,
    name: a.name || null,
    area_name: a.area_name || '',
    old_name: a.name ? null : a.area_name || '',
    photo: a.photo || null,
    photo_opacity: a.photo_opacity || 50,
    objects: a.drawn ? (a.objects || []).map((o) => ({ ...o, key: newKey('x') })) : roomWalls(),
  }))
  const tables = (res.tables || []).map(toTable)
  const off = (res.off_tables || []).map(toTable)
  // Tables never placed get a place, area by area, the same on every device.
  for (const a of areas) autoPlace([...tables, ...off].filter((tb) => sameName(tb.area, a.area_name)).sort(byNumber))
  data.areas = areas
  data.tables = tables
  data.off = off
  data.loose = res.loose || []
  data.upcoming = res.upcoming || []
  data.plan = res.plan || { on: true, can_edit: false }
  if (res.now) clockSkew = Date.now() - serverTime(res.now)
  if (!data.plan.on) view.value = 'list'
  const keys = areas.map((a) => a.key)
  if (areaSel.value !== 'all' && !keys.includes(areaSel.value)) areaSel.value = keys[0] || 'all'
  if (selected.value && !tableByName(selected.value)) closePanel()
  refreshBill()
}

async function load() {
  if (session.offline || editing.value) {
    loading.value = false
    return
  }
  try {
    applyFloor(await call('lumen_restaurants.api.restaurant.get_floor', { pos_profile: session.posProfile }))
  } catch (e) {
    session.notify(e.message, true)
  } finally {
    loading.value = false
  }
}

const tableByName = (name) => data.tables.find((x) => x.name === name) || null
const areaOfTable = (tb) => data.areas.find((a) => sameName(a.area_name, tb.area)) || null
const hasTables = computed(() => data.tables.length > 0 || data.off.length > 0)
function statusOf(tb) {
  if (tb.disabled) return 'off'
  if (tb.order) return tb.order.bill_printed_at ? 'bill' : 'busy'
  if (tb.booking) return 'book'
  return 'free'
}
const tableLabel = (tb) => t('Table {no}', { no: tb.table_no })
function eligible(tb) {
  if (!pick.value || tb.name === pick.value.from) return false
  if (pick.value.kind === 'move') return statusOf(tb) === 'free'
  return Boolean(tb.order)
}

// ---- areas, tabs and views -----------------------------------------------------
const showPlan = computed(() => editing.value || (view.value === 'plan' && data.plan.on && data.areas.length > 0))
const areaList = computed(() => (editing.value ? draft.value.areas : data.areas))
function setArea(key) {
  areaSel.value = key
  sel.value = null
  confirmDelete.value = false
  if (editPanel.value !== 'props') editPanel.value = 'props'
}
function setView(v) {
  view.value = v
  if (v === 'plan' && areaSel.value === 'all') areaSel.value = data.areas[0]?.key || 'all'
}
const liveTablesIn = (key) => {
  const a = data.areas.find((x) => x.key === key)
  return a ? data.tables.filter((tb) => sameName(tb.area, a.area_name)) : []
}
function countText(key) {
  const list = key ? liveTablesIn(key) : data.tables
  return `${list.filter((x) => x.order).length}/${list.length}`
}
const listSections = computed(() => {
  const areas = areaSel.value === 'all' ? data.areas : data.areas.filter((a) => a.key === areaSel.value)
  return areas
    .map((a) => ({ key: a.key, label: areaLabel(a), tables: liveTablesIn(a.key).slice().sort(byNumber) }))
    .filter((s) => s.tables.length)
})
const legend = computed(() => {
  const list = areaSel.value === 'all' || !areaSel.value ? data.tables : liveTablesIn(areaSel.value)
  const out = { free: 0, busy: 0, bill: 0, book: 0, guests: 0 }
  for (const tb of list) {
    out[statusOf(tb)] += 1
    if (tb.order) out.guests += tb.order.guests || 0
  }
  return out
})
// The legend counts the area on screen, Right now the whole floor: one label
// each, so the two counts of guests never read as the same thing.
const legendGuests = computed(() => {
  const a = areaSel.value && areaSel.value !== 'all' ? data.areas.find((x) => x.key === areaSel.value) : null
  return a ? t('Guests in {area}', { area: areaLabel(a) }) : t('Guests now')
})
const nowStats = computed(() => {
  const occ = data.tables.filter((tb) => tb.order)
  let longest = null
  for (const tb of occ) {
    const m = minutesSince(tb.order.opened_at)
    if (!longest || m > longest.m) longest = { m, table_no: tb.table_no }
  }
  return {
    busy: occ.length,
    total: data.tables.length,
    guests: occ.reduce((s, tb) => s + (tb.order.guests || 0), 0),
    value: occ.reduce((s, tb) => s + (tb.order.total || 0), 0),
    longest: longest ? { text: dur(longest.m), table_no: longest.table_no } : null,
  }
})
const upcomingRows = computed(() =>
  data.upcoming.map((b) => ({
    ...b,
    place: b.table ? (b.area || '').trim() || t('Main hall') : b.customer_name || '',
  }))
)

// ---- the plan's drawing ----------------------------------------------------------
const planArea = computed(() => {
  if (editing.value) return editArea.value
  return data.areas.find((a) => a.key === areaSel.value) || data.areas[0] || null
})
const planTables = computed(() => {
  if (!planArea.value) return []
  if (editing.value) {
    return draftTablesIn(planArea.value.key).map((tb) => {
      const live = tableByName(tb.name)
      const status = tb.disabled ? 'off' : live ? statusOf(live) : 'free'
      return {
        ...tb,
        status,
        sub: tb.disabled ? t('Out of service') : t('{n} seats', { n: tb.seats }),
        badge: null,
        aria: `${t('Table {no}', { no: tb.table_no })}, ${statusLabel(status)}`,
        selected: sel.value?.kind === 'table' && sel.value.key === tb.key,
        eligible: false,
      }
    })
  }
  return liveTablesIn(planArea.value.key).map((tb) => {
    const status = statusOf(tb)
    let sub = ''
    let badge = null
    if (tb.order) {
      sub = Number(tb.order.total || 0).toFixed(2)
      badge = { kind: status, text: sinceText(tb.order.opened_at) }
    } else if (tb.booking) {
      sub = t('{n} guests', { n: tb.booking.guests })
      badge = { kind: 'book', text: clockOf(tb.booking.time, t) }
    }
    return {
      key: tb.name,
      table_no: tb.table_no,
      shape: tb.shape,
      seats: tb.seats,
      x: tb.x,
      y: tb.y,
      rot: tb.rot,
      status,
      sub,
      badge,
      aria: `${tableLabel(tb)}, ${statusLabel(status)}${tb.order ? `, ${money(tb.order.total)}` : ''}`,
      selected: selected.value === tb.name,
      eligible: eligible(tb),
    }
  })
})

// ---- a table, picked -------------------------------------------------------------
const selTable = computed(() => (selected.value ? tableByName(selected.value) : null))
const panelOpen = computed(() =>
  editing.value ? Boolean(sel.value) || editPanel.value !== 'props' : Boolean(selTable.value)
)

function selectTable(name) {
  const tb = tableByName(name)
  if (!tb) return
  selected.value = name
  panelMode.value = 'table'
  guestsDraft.value = Math.max(1, tb.seats || 2)
  noteDraft.value = ''
  cancelReason.value = ''
  bill.value = null
  billFor = ''
  refreshBill()
}
function closePanel() {
  selected.value = null
  panelMode.value = 'table'
  pick.value = null
  bill.value = null
  billFor = ''
}

// The bill in the panel is the till's own pricing of the order, fetched again
// when the order changes on another device.
async function refreshBill() {
  const order = selTable.value?.order
  if (!order || !order.lines) {
    bill.value = null
    billFor = ''
    return
  }
  const sig = `${order.name}|${order.total}|${order.lines}|${order.bill_printed_at || ''}`
  if (sig === billFor) return
  billFor = sig
  billLoading.value = true
  try {
    const res = await call('lumen_restaurants.api.restaurant.get_bill', { name: order.name })
    if (billFor === sig) bill.value = res
  } catch {
    if (billFor === sig) bill.value = null
  } finally {
    billLoading.value = false
  }
}

function tapTable(name) {
  if (pick.value) return pickTarget(name)
  selectTable(name)
}

async function goToOrder(order) {
  await cart.openOrder(order)
  router.push('/')
}

async function startOrder() {
  if (!canOpen.value) return session.notify(t('You are not allowed to open a table order'), true)
  const tb = selTable.value
  busy.value = true
  try {
    const order = await call('lumen_restaurants.api.restaurant.open_order', {
      pos_profile: session.posProfile,
      table: tb.name,
      order_type: 'Dine in',
      guests: guestsDraft.value || 0,
      note: noteDraft.value || null,
    })
    await goToOrder(order)
  } catch (e) {
    session.notify(e.message, true)
  } finally {
    busy.value = false
  }
}

async function newTakeaway() {
  busy.value = true
  try {
    const order = await call('lumen_restaurants.api.restaurant.open_order', {
      pos_profile: session.posProfile,
      table: null,
      order_type: 'Takeaway',
      guests: 0,
      note: null,
    })
    await goToOrder(order)
  } catch (e) {
    session.notify(e.message, true)
  } finally {
    busy.value = false
  }
}

async function openOrder(name) {
  try {
    await goToOrder(await call('lumen_restaurants.api.restaurant.get_order', { name }))
  } catch (e) {
    session.notify(e.message, true)
  }
}

// A booking's guests arrived: the booking says Seated and the order opens on
// its table (reservations.set_reservation_status), as on the Bookings screen.
async function seat() {
  const booking = selTable.value?.booking
  if (!booking) return
  busy.value = true
  try {
    const res = await call('lumen_restaurants.api.reservations.set_reservation_status', { name: booking.name, status: 'Seated' })
    if (res.order) await openOrder(res.order.name)
    else await load()
  } catch (e) {
    session.notify(e.message, true)
  } finally {
    busy.value = false
  }
}

function gotoBooking(b) {
  if (b.table && tableByName(b.table)) {
    const tb = tableByName(b.table)
    const a = areaOfTable(tb)
    if (a) areaSel.value = a.key
    if (data.plan.on && !phone) view.value = 'plan'
    selectTable(tb.name)
  } else {
    router.push('/reservations')
  }
}

// ---- move and merge, picked on the plan ---------------------------------------
const pickFrom = computed(() => (pick.value ? tableByName(pick.value.from) : null))
function startPick(kind) {
  pick.value = { kind, from: selected.value }
}
async function pickTarget(name) {
  const src = pickFrom.value
  const dst = tableByName(name)
  if (!src || !src.order || !dst) {
    pick.value = null
    return
  }
  if (dst.name === src.name) return
  busy.value = true
  try {
    if (pick.value.kind === 'move') {
      if (statusOf(dst) !== 'free') return session.notify(t('Pick a free table'), true)
      await call('lumen_restaurants.api.restaurant.move_order', { name: src.order.name, table: dst.name })
      session.notify(t('Moved the order from {a} to {b}', { a: tableLabel(src), b: tableLabel(dst) }))
    } else {
      if (!dst.order) return session.notify(t('Pick a table with an order'), true)
      await call('lumen_restaurants.api.restaurant.merge_orders', { source: src.order.name, target: dst.order.name })
      session.notify(t('Merged the order of {a} into {b}', { a: tableLabel(src), b: tableLabel(dst) }))
    }
    pick.value = null
    await load()
    const a = areaOfTable(dst)
    if (a && areaSel.value !== 'all') areaSel.value = a.key
    selectTable(dst.name)
  } catch (e) {
    session.notify(e.message, true)
  } finally {
    busy.value = false
  }
}
async function moveOffFloor() {
  const src = pickFrom.value
  if (!src?.order) return
  busy.value = true
  try {
    await call('lumen_restaurants.api.restaurant.move_order', { name: src.order.name, table: null })
    session.notify(t('Moved the order of {a} to the takeaway counter', { a: tableLabel(src) }))
    closePanel()
    await load()
  } catch (e) {
    session.notify(e.message, true)
  } finally {
    busy.value = false
  }
}

async function cancelOrder() {
  const tb = selTable.value
  if (!tb?.order) return
  busy.value = true
  try {
    await call('lumen_restaurants.api.restaurant.cancel_order', { name: tb.order.name, reason: cancelReason.value || null })
    session.notify(t('The order on {table} was cancelled', { table: tableLabel(tb) }))
    closePanel()
    await load()
  } catch (e) {
    session.notify(e.message, true)
  } finally {
    busy.value = false
  }
}

// ---- the bill ----------------------------------------------------------------------
const billToPrint = ref(null)
async function printBill() {
  const tb = selTable.value
  if (!tb?.order) return
  busy.value = true
  try {
    const res = await call('lumen_restaurants.api.restaurant.print_bill', {
      name: tb.order.name,
      printer: session.printerConfigured ? 1 : 0,
    })
    if (res.printer_error) session.notify(t('Printer failed ({error}), using browser print', { error: res.printer_error }), true)
    if (!res.printed) {
      // The browser prints it, our mark at its foot like every receipt.
      billToPrint.value = res.bill
      await nextTick()
      window.print()
      billToPrint.value = null
    }
    session.notify(t('The bill for {table} went to the printer. The table is now waiting to pay.', { table: tableLabel(tb) }))
    await load()
  } catch (e) {
    session.notify(e.message, true)
  } finally {
    busy.value = false
  }
}

// ---- paying a table from its panel: the till's own payment window ------------
const paymentOpen = ref(false)
const receipt = ref(null)
let paying = null
async function payTable() {
  const tb = selTable.value
  if (!tb?.order) return
  // A basket being rung up on the order screen is not thrown away for this.
  if (cart.lines.length && !cart.order) {
    return session.notify(t('A sale is in progress on the order screen. Finish it or clear it first.'), true)
  }
  busy.value = true
  try {
    if (cart.order && cart.order.name !== tb.order.name) await cart.leaveOrder()
    const order = await call('lumen_restaurants.api.restaurant.get_order', { name: tb.order.name })
    await cart.openOrder(order)
    // Where the restaurant made the salesperson required, the order screen
    // asks for one first (the server refuses it too).
    if (session.settings.salesperson_mode === 'Required' && session.salesPersons.length && !cart.salesPerson) {
      session.notify(t('Pick the salesperson first'), true)
      router.push('/')
      return
    }
    paying = { table: tableLabel(tb) }
    paymentOpen.value = true
  } catch (e) {
    session.notify(e.message, true)
  } finally {
    busy.value = false
  }
}
async function closePayment() {
  paymentOpen.value = false
  paying = null
  try {
    await cart.leaveOrder()
  } catch {
    // nothing changed on it, the order stays as it was
  }
}
function onPaid(saleReceipt) {
  paymentOpen.value = false
  receipt.value = saleReceipt
}
function closeReceipt() {
  receipt.value = null
  if (paying) session.notify(t('Sale complete. {table} is free again.', { table: paying.table }))
  paying = null
  closePanel()
  load()
}

// ---- edit mode ---------------------------------------------------------------------
const editing = ref(false)
const draft = ref(null)
const sel = ref(null) // { kind: 'table' | 'fx', key }
const editPanel = ref('props')
const menu = ref(null)
const confirmDelete = ref(false)
const areaDraft = ref('')
const areaNameInput = ref(null)
const saving = ref(false)
const photoBusy = ref(false)

const editArea = computed(() => {
  if (!editing.value || !draft.value) return null
  return draft.value.areas.find((a) => a.key === areaSel.value) || draft.value.areas[0] || null
})
const draftTablesIn = (key) => (draft.value ? draft.value.tables.filter((tb) => tb.areaKey === key) : [])
const selTableDraft = computed(() =>
  sel.value?.kind === 'table' ? draft.value?.tables.find((tb) => tb.key === sel.value.key) || null : null
)
const selFxDraft = computed(() =>
  sel.value?.kind === 'fx' ? editArea.value?.objects.find((f) => f.key === sel.value.key) || null : null
)

function startEdit() {
  if (!data.plan.can_edit) return
  const areas = data.areas.map((a) => ({
    ...a,
    area_name: (a.area_name || '').trim() || t('Main hall'),
    objects: a.objects.map((o) => ({ ...o })),
  }))
  if (!areas.length) {
    areas.push({
      key: newKey('a'),
      name: null,
      area_name: t('Main hall'),
      old_name: null,
      photo: null,
      photo_opacity: 50,
      objects: roomWalls(t('Entrance')),
    })
  }
  const keyOf = (name) => (areas.find((a) => a.key === data.areas.find((d) => sameName(d.area_name, name))?.key) || areas[0]).key
  const tables = [...data.tables, ...data.off].map((tb) => ({
    name: tb.name,
    key: tb.name,
    table_no: tb.table_no,
    areaKey: keyOf(tb.area),
    seats: tb.seats || NEW_SEATS[tb.shape] || 4,
    shape: tb.shape,
    x: tb.x,
    y: tb.y,
    rot: tb.rot,
    disabled: tb.disabled,
    hasOrder: Boolean(tb.order),
  }))
  draft.value = { areas, tables, deletedTables: [], deletedAreas: [] }
  editing.value = true
  view.value = 'plan'
  if (areaSel.value === 'all' || !areas.some((a) => a.key === areaSel.value)) areaSel.value = areas[0].key
  sel.value = null
  menu.value = null
  editPanel.value = 'props'
  confirmDelete.value = false
  closePanel()
}

function endEdit() {
  editing.value = false
  draft.value = null
  sel.value = null
  menu.value = null
  editPanel.value = 'props'
  confirmDelete.value = false
}
function cancelEdit() {
  endEdit()
  session.notify(t('Changes discarded'))
  load()
}

const isDup = (tb) =>
  draft.value.tables.some((x) => x.key !== tb.key && String(x.table_no).trim() === String(tb.table_no).trim())
function nextNo() {
  let m = 0
  for (const tb of draft.value.tables) {
    const n = parseInt(tb.table_no, 10)
    if (n > m) m = n
  }
  return String(m + 1)
}
function fixNumber() {
  const tb = selTableDraft.value
  if (tb && !String(tb.table_no).trim()) tb.table_no = nextNo()
}

function pickItem({ kind, key }) {
  sel.value = { kind, key }
  editPanel.value = 'props'
  confirmDelete.value = false
  menu.value = null
}
function dragItem({ kind, key, x, y }) {
  const item = kind === 'table' ? draft.value.tables.find((tb) => tb.key === key) : editArea.value?.objects.find((f) => f.key === key)
  if (!item) return
  item.x = x
  item.y = y
}
function blank() {
  sel.value = null
  menu.value = null
  confirmDelete.value = false
}
function deselect() {
  sel.value = null
  confirmDelete.value = false
}
function openEditPanel(which) {
  editPanel.value = which
  sel.value = null
  menu.value = null
  if (which === 'area') {
    areaDraft.value = ''
    nextTick(() => areaNameInput.value?.focus())
  }
}

// A new table or item lands on the floor where no table stands, the middle
// first: under a table it could not be picked up again.
function freeSpot(areaKey, room = 90) {
  const taken = draftTablesIn(areaKey)
  const spots = []
  for (let y = 110; y <= 540; y += 20) for (let x = 90; x <= 910; x += 20) spots.push([x, y])
  spots.sort((p, q) => Math.hypot(p[0] - 500, p[1] - 320) - Math.hypot(q[0] - 500, q[1] - 320))
  return spots.find(([x, y]) => taken.every((tb) => Math.hypot(tb.x - x, tb.y - y) >= room)) || [500, 320]
}

function addTable(shape) {
  const a = editArea.value
  const [x, y] = freeSpot(a.key, 120)
  const tb = {
    name: null,
    key: newKey('t'),
    table_no: nextNo(),
    areaKey: a.key,
    seats: NEW_SEATS[shape],
    shape,
    x,
    y,
    rot: 0,
    disabled: false,
    hasOrder: false,
  }
  draft.value.tables.push(tb)
  pickItem({ kind: 'table', key: tb.key })
}
function addFx(kind) {
  const d = FX_NEW[kind]
  const [x, y] = freeSpot(editArea.value.key, kind === 'plant' ? 70 : 110)
  const f = { key: newKey('x'), kind, x, y, w: d.w, h: d.h, rot: 0, label: '' }
  editArea.value.objects.push(f)
  pickItem({ kind: 'fx', key: f.key })
}
function addSeats(step) {
  const tb = selTableDraft.value
  const [low, high] = SEAT_RANGE[tb.shape]
  tb.seats = clamp(tb.seats + step, low, high)
}
function setShape(shape) {
  const tb = selTableDraft.value
  const [low, high] = SEAT_RANGE[shape]
  tb.shape = shape
  tb.seats = clamp(tb.seats, low, high)
}
function rotate(step) {
  const item = selTableDraft.value || selFxDraft.value
  if (item) item.rot = norm((item.rot || 0) + step)
}
function moveToArea(key) {
  const tb = selTableDraft.value
  const a = draft.value.areas.find((x) => x.key === key)
  if (!tb || !a) return
  tb.areaKey = key
  sel.value = null
  session.notify(t('Moved the table to {name}', { name: areaLabel(a) }))
}
function setOff(event) {
  const tb = selTableDraft.value
  if (event.target.checked && tb.hasOrder) {
    event.target.checked = false
    return session.notify(t('This table has an open order. Move or close it first.'), true)
  }
  tb.disabled = event.target.checked
}
function askDelete() {
  if (selTableDraft.value?.hasOrder) return session.notify(t('This table has an open order. Move or close it first.'), true)
  confirmDelete.value = true
}
function deleteTable() {
  const tb = selTableDraft.value
  if (!tb) return
  if (tb.name) draft.value.deletedTables.push(tb.name)
  draft.value.tables = draft.value.tables.filter((x) => x.key !== tb.key)
  sel.value = null
  confirmDelete.value = false
}
function deleteFx() {
  const f = selFxDraft.value
  if (!f) return
  editArea.value.objects = editArea.value.objects.filter((x) => x.key !== f.key)
  sel.value = null
}
function addArea() {
  const name = areaDraft.value.trim()
  if (!name) return areaNameInput.value?.focus()
  if (draft.value.areas.some((a) => sameName(a.area_name, name))) {
    return session.notify(t('Two areas are named {name}', { name }), true)
  }
  const a = { key: newKey('a'), name: null, area_name: name, old_name: null, photo: null, photo_opacity: 50, objects: roomWalls() }
  draft.value.areas.push(a)
  areaSel.value = a.key
  editPanel.value = 'props'
  areaDraft.value = ''
  session.notify(t('Added the area {name}', { name }))
}
function deleteArea() {
  const a = editArea.value
  if (!a || draftTablesIn(a.key).length || draft.value.areas.length < 2) return
  if (a.name) draft.value.deletedAreas.push(a.name)
  draft.value.areas = draft.value.areas.filter((x) => x.key !== a.key)
  areaSel.value = draft.value.areas[0].key
}

// A photo of the real floor, made smaller on the device first: a phone's
// photo is several megabytes, the plan needs a fraction of it.
function shrink(file) {
  return new Promise((resolve) => {
    if (!/^image\/(png|jpe?g|webp)$/i.test(file.type)) return resolve(file)
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      const scale = Math.min(1, 1600 / Math.max(img.width, img.height))
      if (scale === 1 && file.size < 1500000) {
        URL.revokeObjectURL(url)
        return resolve(file)
      }
      const canvas = document.createElement('canvas')
      canvas.width = Math.round(img.width * scale)
      canvas.height = Math.round(img.height * scale)
      const ctx = canvas.getContext('2d')
      ctx.fillStyle = '#ffffff'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
      URL.revokeObjectURL(url)
      canvas.toBlob((blob) => resolve(blob || file), 'image/jpeg', 0.85)
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      resolve(file)
    }
    img.src = url
  })
}
async function choosePhoto(event) {
  const file = event.target.files?.[0]
  const area = editArea.value
  if (!file || !area) return
  photoBusy.value = true
  try {
    const blob = await shrink(file)
    const form = new FormData()
    form.append('file', blob, blob === file ? file.name : 'floor-plan.jpg')
    // Staff only: the area it belongs to opens it to whoever sees the floor.
    form.append('is_private', '1')
    form.append('folder', 'Home')
    const res = await fetch('/api/method/upload_file', {
      method: 'POST',
      headers: { 'X-Frappe-CSRF-Token': window.csrf_token || '', Accept: 'application/json' },
      body: form,
    })
    const out = await res.json()
    if (!res.ok || !out.message?.file_url) throw new Error(t('The picture could not be uploaded'))
    area.photo = out.message.file_url
  } catch (e) {
    session.notify(e.message, true)
  } finally {
    photoBusy.value = false
    event.target.value = ''
  }
}

async function saveEdit() {
  const d = draft.value
  for (const a of d.areas) {
    if (!a.area_name.trim()) {
      areaSel.value = a.key
      sel.value = null
      return session.notify(t('Give every area a name'), true)
    }
  }
  const dup = d.tables.find((tb) => isDup(tb))
  if (dup) {
    areaSel.value = dup.areaKey
    pickItem({ kind: 'table', key: dup.key })
    return session.notify(t('Another table already has this number'), true)
  }
  const nameOf = Object.fromEntries(d.areas.map((a) => [a.key, a.area_name.trim()]))
  const plan = {
    areas: d.areas.map((a) => ({
      name: a.name,
      area_name: a.area_name.trim(),
      old_name: a.name ? null : a.old_name,
      photo: a.photo || null,
      photo_opacity: a.photo_opacity || 50,
      objects: a.objects.map((f) => ({ kind: f.kind, label: f.label || '', x: f.x, y: f.y, w: f.w, h: f.h, rot: f.rot || 0 })),
    })),
    tables: d.tables.map((tb) => ({
      name: tb.name,
      table_no: String(tb.table_no).trim(),
      area: nameOf[tb.areaKey],
      seats: tb.seats,
      shape: tb.shape,
      x: tb.x,
      y: tb.y,
      rot: tb.rot || 0,
      disabled: tb.disabled ? 1 : 0,
    })),
    deleted_tables: d.deletedTables,
    deleted_areas: d.deletedAreas,
  }
  saving.value = true
  try {
    const res = await call('lumen_restaurants.api.floor.save_plan', { pos_profile: session.posProfile, plan })
    const keep = areaLabel(editArea.value)
    endEdit()
    applyFloor(res)
    const back = data.areas.find((a) => sameName(areaLabel(a), keep))
    if (back) areaSel.value = back.key
    session.notify(t('Plan saved'))
  } catch (e) {
    session.notify(e.message, true)
  } finally {
    saving.value = false
  }
}

// ---- keys, clocks and the poll -------------------------------------------------------
function onKey(e) {
  if (e.key !== 'Escape') return
  if (menu.value) menu.value = null
  else if (pick.value) pick.value = null
  else if (editing.value && editPanel.value !== 'props') editPanel.value = 'props'
  else if (editing.value && sel.value) sel.value = null
  else if (!editing.value && selected.value) closePanel()
}
function onDocClick() {
  if (menu.value) menu.value = null
}

watch(
  () => [selTable.value?.order?.total, selTable.value?.order?.lines, selTable.value?.order?.bill_printed_at],
  () => refreshBill()
)

onMounted(() => {
  load()
  ticker = setInterval(() => (now.value = Date.now()), 30000)
  // Another waiter can open, move or pay a table while this screen is up.
  poll = setInterval(load, 15000)
  document.addEventListener('keydown', onKey)
  document.addEventListener('click', onDocClick)
})
onUnmounted(() => {
  clearInterval(ticker)
  clearInterval(poll)
  document.removeEventListener('keydown', onKey)
  document.removeEventListener('click', onDocClick)
})
</script>
