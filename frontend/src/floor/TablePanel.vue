<!-- Copyright (c) 2026 Lumen Solutions
     SPDX-License-Identifier: AGPL-3.0-only
     Lumen Restaurants 0.1.0-r14: the panel of one table on the floor plan, as
     in the approved mockup. A free table starts an order, a booked one seats
     its guests, a table with an order shows it priced as the guests will pay
     it (restaurant.get_bill) and pays, prints the bill, moves, merges or
     cancels. Paying opens the till's own payment window: one way to take
     money in the whole app. -->
<template>
  <div class="p-head">
    <span class="p-title">{{ t('Table {no}', { no: table.table_no }) }}</span>
    <span class="chip" :class="'s-' + status">
      <FloorIcon v-if="status === 'bill'" name="receipt" class="chip-ic" />{{ statusLabel }}
    </span>
    <span class="grow"></span>
    <button type="button" class="btn btn-ghost icon-btn" :aria-label="t('Close')" @click="$emit('close')">
      <FloorIcon name="close" />
    </button>
  </div>

  <!-- Cancelling the order: the reason is the only record there is. -->
  <template v-if="order && mode === 'cancel'">
    <div class="p-body">
      <p class="hint">{{ t('Nothing was paid, so nothing is refunded. Say why, it is the only record there is.') }}</p>
      <label class="field">
        <span class="field-label">{{ t('Reason') }}</span>
        <input ref="reasonInput" v-model="reason" class="input" autocomplete="off" @keyup.enter="$emit('cancel-confirm')" />
      </label>
    </div>
    <div class="p-foot">
      <button type="button" class="btn btn-danger btn-block" :disabled="busy" @click="$emit('cancel-confirm')">
        <FloorIcon name="trash" />{{ t('Cancel the order') }}
      </button>
      <button type="button" class="btn btn-outline btn-block" @click="$emit('back')">{{ t('Back') }}</button>
    </div>
  </template>

  <template v-else-if="order">
    <div class="p-body">
      <div class="meta">
        <div><small>{{ t('Guests') }}</small><b>{{ order.guests || 0 }}</b></div>
        <div><small>{{ t('Sitting for') }}</small><b>{{ sitting }}</b></div>
        <div><small>{{ t('Area') }}</small><b>{{ areaLabel }}</b></div>
        <div><small>{{ t('Opened by') }}</small><b>{{ order.opened_by_name || '' }}</b></div>
      </div>
      <p v-if="order.note" class="note-box"><FloorIcon name="edit" /><span>{{ order.note }}</span></p>
      <div class="sec">
        <div class="sec-title">{{ t('floor:Order') }}</div>
        <p v-if="!order.lines" class="hint">{{ t('No items yet. Items are added on the sell screen.') }}</p>
        <p v-else-if="billLoading && !bill" class="hint">{{ t('Loading…') }}</p>
        <template v-else-if="bill">
          <div class="items">
            <div v-for="(it, i) in bill.items" :key="i" class="item" :class="{ addon: it.addon_of }">
              <span>
                <template v-if="it.addon_of">+ {{ it.item_name }}</template>
                <template v-else><span class="q">{{ it.qty }}×</span> {{ it.item_name }}</template>
                <small v-if="it.choices_text" class="choices">{{ it.choices_text }}</small>
              </span>
              <span class="num">{{ money(it.amount, bill.currency) }}</span>
            </div>
          </div>
          <div class="sums">
            <div v-if="bill.discount_amount" class="sum">
              <span>{{ t('Discount') }}</span><span class="num">-{{ money(bill.discount_amount, bill.currency) }}</span>
            </div>
            <div v-if="bill.taxes.length" class="sum">
              <span>{{ t('Before VAT') }}</span><span class="num">{{ money(bill.net_total, bill.currency) }}</span>
            </div>
            <div v-for="tax in bill.taxes" :key="tax.description" class="sum">
              <span>{{ tax.description }}</span><span class="num">{{ money(tax.tax_amount, bill.currency) }}</span>
            </div>
            <div class="sum total">
              <span>{{ t('Total') }}</span><span class="num">{{ money(due, bill.currency) }}</span>
            </div>
            <p v-if="bill.estimated" class="hint">{{ t('An estimate: the till prices it when it is paid.') }}</p>
          </div>
        </template>
      </div>
    </div>
    <div class="p-foot">
      <button
        v-if="perms.sell"
        type="button"
        class="btn btn-primary btn-lg btn-block"
        :disabled="busy || !order.lines"
        @click="$emit('pay')"
      >
        <FloorIcon name="pay" />{{ t('Pay') }}<template v-if="order.lines">&nbsp;{{ money(due, bill?.currency) }}</template>
      </button>
      <div class="row-2">
        <button type="button" class="btn btn-outline" :disabled="busy || !order.lines" @click="$emit('print')">
          <FloorIcon name="print" />{{ status === 'bill' ? t('Reprint the bill') : t('Print the bill') }}
        </button>
        <button type="button" class="btn btn-outline" :disabled="busy" @click="$emit('open')">
          <FloorIcon name="list" />{{ t('Open the order') }}
        </button>
      </div>
      <div v-if="perms.move" class="row-2">
        <button type="button" class="btn btn-outline" :disabled="busy" @click="$emit('move')">
          <FloorIcon name="move" />{{ t('Move') }}
        </button>
        <button type="button" class="btn btn-outline" :disabled="busy" @click="$emit('merge')">
          <FloorIcon name="merge" />{{ t('Merge') }}
        </button>
      </div>
      <button v-if="perms.cancel" type="button" class="link-danger" @click="$emit('cancel-start')">
        {{ t('Cancel the order') }}
      </button>
    </div>
  </template>

  <template v-else-if="booking">
    <div class="p-body">
      <div class="meta">
        <div><small>{{ t('Booked for') }}</small><b>{{ clockOf(booking.time, t) }}</b></div>
        <div><small>{{ t('Party size') }}</small><b>{{ booking.guests }}</b></div>
        <div><small>{{ t('Area') }}</small><b>{{ areaLabel }}</b></div>
        <div><small>{{ t('Source') }}</small><b>{{ booking.source === 'Online' ? t('Booking page') : t('Taken by the staff') }}</b></div>
      </div>
      <div v-if="booking.customer_name" class="meta one">
        <div><small>{{ t('Name') }}</small><b>{{ booking.customer_name }}</b></div>
      </div>
      <p class="hint">{{ t('The table is held for this booking. When the guests arrive, tap Seated to open their order.') }}</p>
    </div>
    <div v-if="perms.open" class="p-foot">
      <button type="button" class="btn btn-primary btn-lg btn-block" :disabled="busy" @click="$emit('seated')">
        <FloorIcon name="check" />{{ t('Seated') }}
      </button>
    </div>
  </template>

  <template v-else>
    <div class="p-body">
      <div class="meta">
        <div><small>{{ t('Area') }}</small><b>{{ areaLabel }}</b></div>
        <div><small>{{ t('Seats') }}</small><b>{{ table.seats }}</b></div>
      </div>
      <template v-if="perms.open">
        <div class="field">
          <span class="field-label">{{ t('Guests') }}</span>
          <div class="stepper">
            <button type="button" class="btn btn-outline icon-btn" aria-label="-1" @click="guests = Math.max(1, guests - 1)">
              <FloorIcon name="minus" />
            </button>
            <output>{{ guests }}</output>
            <button type="button" class="btn btn-outline icon-btn" aria-label="+1" @click="guests = Math.min(40, guests + 1)">
              <FloorIcon name="plus" />
            </button>
          </div>
        </div>
        <label class="field">
          <span class="field-label">{{ t('Note') }}</span>
          <input
            v-model="note"
            class="input"
            :placeholder="t('Anything the kitchen or the next cashier should know')"
            autocomplete="off"
            @keyup.enter="$emit('start')"
          />
        </label>
        <p class="hint">{{ t('Pick the number of guests and start the order. You then go to the sell screen to add items.') }}</p>
      </template>
      <p v-else class="hint">{{ t('You are not allowed to open a table order') }}</p>
    </div>
    <div v-if="perms.open" class="p-foot">
      <button type="button" class="btn btn-primary btn-lg btn-block" :disabled="busy" @click="$emit('start')">
        <FloorIcon name="check" />{{ t('Start the order') }}
      </button>
    </div>
  </template>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { t } from '../i18n'
import { money } from '../format'
import FloorIcon from './FloorIcon.vue'
import { clockOf } from './plan'

const props = defineProps({
  // The live table: { table_no, seats, order, booking, ... }
  table: { type: Object, required: true },
  status: { type: String, required: true },
  statusLabel: { type: String, required: true },
  areaLabel: { type: String, default: '' },
  sitting: { type: String, default: '' },
  bill: { type: Object, default: null },
  billLoading: { type: Boolean, default: false },
  mode: { type: String, default: 'table' },
  busy: { type: Boolean, default: false },
  // { sell, open, move, cancel }
  perms: { type: Object, required: true },
})
defineEmits(['close', 'start', 'seated', 'open', 'pay', 'print', 'move', 'merge', 'cancel-start', 'cancel-confirm', 'back'])

const guests = defineModel('guests', { type: Number, default: 2 })
const note = defineModel('note', { type: String, default: '' })
const reason = defineModel('reason', { type: String, default: '' })

const order = computed(() => props.table.order)
const booking = computed(() => props.table.booking)
// What the guests pay: the till's own pricing when it has come back, else the
// order's running total.
const due = computed(() => {
  const b = props.bill
  if (b && !b.estimated) return b.rounded_total || b.grand_total
  return b ? b.grand_total : order.value?.total || 0
})

const reasonInput = ref(null)
watch(
  () => props.mode,
  (mode) => {
    if (mode === 'cancel') nextTick(() => reasonInput.value?.focus())
  }
)
</script>
