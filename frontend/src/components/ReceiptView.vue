<!-- Copyright (c) 2026 Lumen Solutions
     SPDX-License-Identifier: AGPL-3.0-only
     "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md. -->
<template>
  <div :id="printable ? 'receipt-print' : null" class="receipt" :class="`tpl-${tpl}`">
    <div class="receipt-head">
      <img v-if="s.receipt_logo" :src="s.receipt_logo" class="receipt-logo" alt="" />
      <div class="receipt-company">{{ receipt.company }}</div>
      <div v-if="s.receipt_header" class="muted small receipt-extra">{{ s.receipt_header }}</div>
      <div v-if="s.receipt_show_address && s.receipt_address" class="muted small receipt-extra">
        {{ s.receipt_address }}
      </div>
      <div v-if="s.receipt_show_tax_id && s.receipt_tax_id" class="muted small">
        {{ t('Tax ID') }}: {{ s.receipt_tax_id }}
      </div>
      <div v-if="receipt.is_return" class="return-stamp">{{ t('REFUND') }}</div>
      <!-- Lumen Restaurants 0.1.0-r14: a table's bill, before it is paid. -->
      <template v-if="receipt.is_bill">
        <div class="bill-stamp">{{ t('floor:Bill') }}</div>
        <div v-if="receipt.table_label" class="muted small">
          {{ receipt.table_label }}<span v-if="receipt.guests"> · {{ t('{n} guests', { n: receipt.guests }) }}</span>
        </div>
      </template>
      <div v-if="receipt.order_no" class="order-no-box">
        <span class="onb-label">{{ t('Order number') }}</span>
        <span class="onb-num">{{ receipt.order_no }}</span>
      </div>
      <div class="muted small">
        {{ receipt.name }} · {{ receipt.posting_date }} {{ String(receipt.posting_time || '').split('.')[0] }}
      </div>
      <div class="muted small" v-if="receipt.return_against">{{ t('against') }} {{ receipt.return_against }}</div>
      <div class="muted small">{{ receipt.customer_name }}</div>
      <div class="muted small" v-if="receipt.sales_person">{{ t('Served by') }} {{ receipt.sales_person }}</div>
      <div class="muted small" v-if="receipt.app_type">
        {{ receipt.app_type }}<span v-if="receipt.order_id"> · {{ t('Order') }} {{ receipt.order_id }}</span>
      </div>
      <template v-for="(f, i) in headerCustomFields" :key="'hcf' + i">
        <img v-if="f.render === 'Image'" :src="asImg(f.value)" class="receipt-cf-img" alt="" />
        <div v-else class="muted small receipt-extra">
          <span v-if="f.label">{{ f.label }}: </span>{{ f.value }}
        </div>
      </template>
    </div>

    <table class="receipt-table">
      <tbody>
        <!-- Lumen Restaurants: a paid add-on sits under its dish. -->
        <tr v-for="(item, i) in receipt.items" :key="i" :class="{ 'ritem-addon': item.addon_of }">
          <td v-if="item.addon_of" class="ritem-addon-name">+ {{ item.item_name }}</td>
          <td v-else>
            <div class="ritem-name">{{ item.item_name }}</div>
            <div v-if="item.choices_text" class="muted small ritem-choices">{{ item.choices_text }}</div>
            <div
              v-if="(s.receipt_show_item_code && item.item_code) || (s.receipt_show_barcode && item.barcode)"
              class="muted small ritem-meta"
            >
              <span v-if="s.receipt_show_item_code">{{ item.item_code }}</span>
              <span v-if="s.receipt_show_barcode && item.barcode"> · {{ item.barcode }}</span>
            </div>
            <div v-if="s.receipt_show_serial && item.serial_no" class="muted small ritem-meta">
              {{ t('SN') }}: {{ String(item.serial_no).split('\n').join(', ') }}
            </div>
            <div v-if="s.receipt_show_unit_price" class="muted small">
              {{ item.qty }} × {{ m(item.rate) }}
            </div>
            <div v-else class="muted small">{{ t('Qty') }} {{ item.qty }}</div>
          </td>
          <td class="right">{{ m(item.amount) }}</td>
        </tr>
      </tbody>
    </table>

    <div class="receipt-totals">
      <div v-if="receipt.discount_amount" class="row">
        <span>{{ t('Discount') }}</span><span>-{{ m(receipt.discount_amount) }}</span>
      </div>
      <div v-for="tax in receipt.taxes" :key="tax.description" class="row">
        <span>{{ tax.description }}</span><span>{{ m(tax.tax_amount) }}</span>
      </div>
      <div class="row total">
        <span>{{ t('Total') }}</span><span>{{ m(receipt.rounded_total || receipt.grand_total) }}</span>
      </div>
      <!-- A sale in another currency: its local value and the rate it was sold at. -->
      <template v-if="foreign">
        <div class="row muted small">
          <span>{{ t('In {currency}', { currency: receipt.company_currency }) }}</span>
          <span>{{ money(receipt.base_grand_total, receipt.company_currency) }}</span>
        </div>
        <div class="row muted small">
          <span>{{ t('Rate') }}</span>
          <span>{{ rateLine(receipt.currency, receipt.conversion_rate, receipt.company_currency) }}</span>
        </div>
      </template>
      <template v-if="s.receipt_show_payments">
        <div v-for="payment in paymentRows" :key="payment.mode_of_payment" class="row">
          <span>{{ modeLabel(payment.mode_of_payment) }}</span>
          <span>{{ foreign && payment.currency ? money(payment.tendered, payment.currency) : m(payment.amount) }}</span>
        </div>
      </template>
      <div v-if="receipt.loyalty_amount" class="row">
        <span>{{ t('Loyalty points') }} ({{ receipt.loyalty_points_redeemed }})</span>
        <span>{{ money(receipt.loyalty_amount) }}</span>
      </div>
      <div v-if="receipt.change_amount" class="row">
        <span>{{ t('Change') }}</span>
        <span>{{ foreign && receipt.change_currency !== receipt.currency ? money(receipt.base_change_amount, receipt.company_currency) : m(receipt.change_amount) }}</span>
      </div>
      <!-- A sale on account (0.60.0): what stays owed, on this sale and in
           all, whatever the receipt shows of the payments. -->
      <template v-if="receipt.on_account && !receipt.is_return">
        <div class="row total owed">
          <span>{{ t('Owed on this sale') }}</span><span>{{ m(receipt.on_account.owed_on_sale) }}</span>
        </div>
        <div v-if="receipt.on_account.owed_total != null" class="row muted small">
          <span>{{ t('Owed in all') }}</span><span>{{ money(receipt.on_account.owed_total, receipt.company_currency) }}</span>
        </div>
      </template>
      <template v-else-if="receipt.on_account">
        <div class="row">
          <span>{{ t('Taken off what is owed') }}</span><span>{{ m(Math.abs(receipt.on_account.amount)) }}</span>
        </div>
        <div v-if="receipt.on_account.owed_total != null" class="row muted small">
          <span>{{ t('Owed in all') }}</span><span>{{ money(receipt.on_account.owed_total, receipt.company_currency) }}</span>
        </div>
      </template>
    </div>
    <div v-if="receipt.on_account && !receipt.is_return" class="receipt-sign small">
      {{ t('Customer signature') }}
    </div>

    <div v-if="receipt.applied_promotions?.length" class="receipt-promos">
      <div v-for="promo in receipt.applied_promotions" :key="promo.name" class="muted small">
        ★ {{ promo.title }} ({{ t('saved') }} {{ m(promo.savings) }})
      </div>
    </div>
    <div v-if="receipt.loyalty_points_earned" class="receipt-promos muted small">
      {{ t('Points earned:') }} {{ receipt.loyalty_points_earned }}
    </div>

    <div v-if="s.receipt_show_note && receipt.note" class="receipt-note small">
      <strong>{{ t('Note') }}:</strong> {{ receipt.note }}
    </div>
    <div v-if="s.receipt_show_terms && s.receipt_terms" class="receipt-terms small">
      {{ s.receipt_terms }}
    </div>

    <div v-if="footerCustomFields.length" class="receipt-cf-foot">
      <template v-for="(f, i) in footerCustomFields" :key="'fcf' + i">
        <img v-if="f.render === 'Image'" :src="asImg(f.value)" class="receipt-cf-img" alt="" />
        <div v-else class="muted small receipt-extra">
          <span v-if="f.label">{{ f.label }}: </span>{{ f.value }}
        </div>
      </template>
    </div>

    <div v-if="receipt.is_bill" class="bill-note small">
      <div>{{ t('Not a tax invoice. The tax invoice is issued when the bill is paid.') }}</div>
      <div v-if="receipt.estimated">{{ t('An estimate: the till prices it when it is paid.') }}</div>
    </div>
    <div class="receipt-foot muted small">
      <div v-if="s.receipt_footer" class="receipt-extra">{{ s.receipt_footer }}</div>
      {{ t('Thank you!') }}
    </div>

    <!-- Lumen Restaurants (he chose it, 2026-09-27): our mark small at the foot
         of every receipt, the kit's mini cut, in the brand blues on screen and
         pure black on paper like its receipt cut. The restaurant's own logo
         stays at the top. -->
    <div class="receipt-brand">
      <svg class="rb-mark" viewBox="0 0 48 48" aria-hidden="true">
        <rect class="rb-acc" x="9" y="6" width="6" height="11" rx="3" />
        <rect class="rb-acc" x="18" y="6" width="6" height="11" rx="3" />
        <rect x="9" y="13" width="15" height="7" rx="3.5" />
        <rect x="13" y="13" width="7" height="21" rx="3.5" />
        <rect x="28" y="6" width="11" height="18" rx="5.5" />
        <rect x="28" y="19" width="7" height="15" rx="3.5" />
        <rect class="rb-acc" x="4" y="36" width="40" height="8" rx="4" />
      </svg>
      <span>Lumen Restaurants</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { t } from '../i18n'
import { money, rateLine } from '../format'
import { useSessionStore } from '../stores/session'

const props = defineProps({
  receipt: { type: Object, required: true },
  // Optional settings override (for the live Settings preview); defaults to the
  // session's saved settings.
  settings: { type: Object, default: null },
  // Only the real receipt gets id="receipt-print" so the print stylesheet
  // targets it (the Settings preview must never be the print target).
  printable: { type: Boolean, default: false },
})

const session = useSessionStore()
// The receipt of the outlet that made the sale (sent with it), over this
// till's own: a reprint of another outlet's sale shows that outlet's tax ID,
// address and logo.
const s = computed(
  () => props.settings || { ...(session.settings || {}), ...(props.receipt.receipt_settings || {}) }
)

// Amounts print in the sale's own currency (lumen_restaurants.currency). A sale in
// another currency also shows its local value, the rate, each tender in its own
// money and the change in local money (it always comes out of the main drawer).
const m = (amount) => money(amount, props.receipt.currency)
const foreign = computed(
  () =>
    Boolean(props.receipt.company_currency) &&
    props.receipt.currency !== props.receipt.company_currency &&
    props.receipt.base_grand_total != null
)
const tpl = computed(() => (s.value.receipt_template || 'Standard').toLowerCase())

// Dynamic custom fields resolved by the server (get_receipt), each is
// { label, value, render: 'Text'|'Image', position: 'Header'|'Footer' }.
const cf = computed(() => props.receipt.custom_fields || [])
const headerCustomFields = computed(() => cf.value.filter((f) => f.position === 'Header'))
const footerCustomFields = computed(() => cf.value.filter((f) => f.position !== 'Header'))
function asImg(value) {
  const v = String(value || '').trim()
  if (!v) return ''
  // Accept a data URL, an http(s) URL or a /files path as-is; treat anything
  // else as raw base64 PNG (e.g. a ZATCA QR stored as a base64 string).
  return /^(data:|https?:|\/)/i.test(v) ? v : `data:image/png;base64,${v}`
}

// LumenPOS's own tender for a sale on account reads in the till's language.
function modeLabel(mode) {
  return mode && mode === session.creditMode ? t('On account') : mode
}
// A return's part taken off the debt has its own row, in plain words, so its
// tender line is not printed twice.
const paymentRows = computed(() =>
  (props.receipt.payments || []).filter(
    (p) => !(props.receipt.is_return && props.receipt.on_account && p.mode_of_payment === session.creditMode)
  )
)
</script>

<style scoped>
.receipt {
  border: 1px dashed var(--border);
  border-radius: var(--radius);
  padding: 16px;
  font-size: 13px;
}
.row.owed { margin-top: 6px; }
.receipt-sign {
  margin-top: 26px;
  padding-top: 4px;
  border-top: 1px solid currentColor;
  width: 70%;
}
.receipt-head { text-align: center; margin-bottom: 12px; }
.receipt-logo {
  max-height: 64px;
  max-width: 70%;
  object-fit: contain;
  margin: 0 auto 8px;
  display: block;
}
.receipt-company { font-weight: 800; font-size: 15px; }
.receipt-extra { white-space: pre-line; margin: 3px 0; }
.return-stamp { color: var(--red); font-weight: 800; letter-spacing: 0.2em; }
.bill-stamp { font-weight: 800; font-size: 14px; letter-spacing: 0.06em; margin: 4px 0 2px; }
.bill-note {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed var(--border);
  text-align: center;
  color: var(--text-muted);
}
.receipt-table { width: 100%; border-collapse: collapse; }
.receipt-table td {
  padding: 5px 0;
  border-bottom: 1px solid var(--border-subtle);
  vertical-align: top;
}
.ritem-name { font-weight: 600; }
.ritem-meta { font-family: var(--mono); }
.ritem-choices { font-size: 12px; }
.ritem-addon-name { padding-inline-start: 14px; font-size: 13px; }
.receipt-totals { margin-top: 10px; }
.row { display: flex; justify-content: space-between; padding: 2.5px 0; }
.row.total { font-weight: 800; font-size: 15px; padding: 6px 0; }
.receipt-promos {
  margin-top: 8px;
  border-top: 1px solid var(--border-subtle);
  padding-top: 8px;
}
.receipt-note {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--border-subtle);
  white-space: pre-line;
}
.receipt-terms {
  margin-top: 10px;
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text-muted);
  white-space: pre-line;
}
.receipt-foot { text-align: center; margin-top: 12px; }
.receipt-cf-img { max-width: 60%; max-height: 150px; object-fit: contain; margin: 6px auto; display: block; }
.receipt-cf-foot {
  text-align: center;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--border-subtle);
}
.small { font-size: 11.5px; }

/* ---- Templates ---- */
.tpl-compact { font-size: 11.5px; padding: 12px; border: none; }
.tpl-compact .receipt-company { font-size: 13.5px; }
.tpl-compact .receipt-head { margin-bottom: 8px; }
.tpl-compact .receipt-table td { padding: 3px 0; }
.tpl-compact .row.total { font-size: 13.5px; }

.tpl-detailed { font-size: 13px; padding: 22px; }
.tpl-detailed .receipt-head {
  padding-bottom: 12px;
  margin-bottom: 14px;
  border-bottom: 2px solid var(--border);
}
.tpl-detailed .receipt-company { font-size: 18px; }
.tpl-detailed .receipt-table td { padding: 7px 0; }
.tpl-detailed .row { padding: 4px 0; }
.order-no-box {
  margin: 8px auto 6px;
  border: 2px solid #000;
  border-radius: 10px;
  padding: 4px 10px 7px;
  max-width: 170px;
  text-align: center;
}
.onb-label { display: block; font-size: 10.5px; }
.onb-num { display: block; font-size: 34px; font-weight: 800; line-height: 1.1; }

.receipt-brand {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  margin-top: 10px;
  font-size: 10px;
  color: var(--text-muted);
}
/* The kit's colours: brand blue and the light accent, their dark cut on a
   dark theme. */
.rb-mark { width: 16px; height: 16px; flex: none; fill: #1463ff; }
.rb-mark .rb-acc { fill: #7fa8ff; }
:root[data-theme='dark'] .rb-mark { fill: #2f7bff; }
:root[data-theme='dark'] .rb-mark .rb-acc { fill: #6ba4ff; }
@media print {
  .receipt-brand { color: #000; }
  /* 12 mm, the kit's receipt size (never below 10 mm), all black. */
  .rb-mark { width: 12mm; height: 12mm; }
  .rb-mark,
  .rb-mark .rb-acc,
  :root[data-theme='dark'] .rb-mark,
  :root[data-theme='dark'] .rb-mark .rb-acc { fill: #000; }
}
</style>
