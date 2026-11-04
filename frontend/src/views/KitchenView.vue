<!-- Copyright (c) 2026 Lumen Solutions
     SPDX-License-Identifier: AGPL-3.0-only
     "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md. -->
<template>
  <div class="kds">
    <div class="card kds-card">
      <div class="kds-head">
        <div class="kds-title"><Icon name="bulb" /> {{ t('Kitchen') }}</div>
        <span v-if="avgText" class="kpill">{{ t('Average today: {t}', { t: avgText }) }}</span>
        <span class="kpill">{{ t('{n} live orders', { n: tickets.length }) }}</span>
        <button class="btn btn-outline" @click="load"><Icon name="refresh" /></button>
      </div>

      <div v-if="session.offline" class="kempty muted">{{ t('The kitchen screen needs a connection.') }}</div>
      <div v-else-if="loading" class="kempty muted">{{ t('Loading…') }}</div>
      <div v-else class="kcols">
        <div class="kcol" v-for="col in columns" :key="col.status">
          <h3>{{ t(col.label) }} <span class="kcount">{{ col.tickets.length }}</span></h3>
          <div v-if="!col.tickets.length" class="kempty muted small">{{ t('Nothing here') }}</div>
          <div
            v-for="ticket in col.tickets"
            :key="ticket.name"
            class="kticket"
            :class="{ prep: ticket.status === 'Preparing', ready: ticket.status === 'Ready' }"
          >
            <div class="khead">
              <span class="kno" :class="{ table: !ticket.order_no }">
                {{ ticket.order_no ? '#' + ticket.order_no : ticket.table_label }}
              </span>
              <span class="kbadge" :class="ticket.order_type === 'Dine in' ? 'hall' : 'away'">
                {{ t(ticket.order_type) }}
              </span>
              <span class="ktimer" :class="ageClass(ticket)">{{ ageText(ticket) }}</span>
            </div>
            <ul class="kitems">
              <li v-for="(row, i) in ticket.items" :key="i">
                <b>×{{ row.qty }}</b> {{ row.item_name }}
                <span v-if="row.note" class="knote">{{ row.note }}</span>
                <!-- Lumen Restaurants: the guest's choices, a without in red, heat in
                     amber, doneness in violet, a paid extra in blue. -->
                <span v-if="(row.modifiers || []).length" class="kmods">
                  <span
                    v-for="(choice, c) in row.modifiers"
                    :key="c"
                    class="kmod"
                    :class="choice.p ? 'add' : choice.s || 'plain'"
                  >{{ choice.p ? '+ ' : '' }}{{ choice.t }}</span>
                </span>
              </li>
            </ul>
            <div v-if="ticket.note" class="kfree muted small">{{ ticket.note }}</div>
            <div class="kbtns">
              <button v-if="ticket.status === 'New'" class="kbtn go" @click="advance(ticket, 'Preparing')">
                {{ t('Start preparing') }}
              </button>
              <button v-else-if="ticket.status === 'Preparing'" class="kbtn done" @click="advance(ticket, 'Ready')">
                {{ t('Ready') }}
              </button>
              <button v-else class="kbtn hand" @click="advance(ticket, 'Done')">
                {{ t('Handed over') }}
              </button>
              <button class="kbtn print" :title="t('Print the kitchen slip')" @click="printSlip(ticket)">
                <Icon name="report" />
              </button>
            </div>
            <div v-if="ticket.status === 'Ready'" class="kready-note">
              {{ ticket.order_no ? t('Call number {n}', { n: ticket.order_no }) : t('Take it to {t}', { t: ticket.table_label }) }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import Icon from '../components/Icon.vue'
import { call } from '../api'
import { useSessionStore } from '../stores/session'
import { t } from '../i18n'

const session = useSessionStore()
const tickets = ref([])
const avgSeconds = ref(0)
const loading = ref(true)
const now = ref(Date.now())
let clockSkew = 0
let poll = null
let ticker = null

const columns = computed(() => [
  { status: 'New', label: 'New orders', tickets: tickets.value.filter((x) => x.status === 'New') },
  { status: 'Preparing', label: 'Preparing', tickets: tickets.value.filter((x) => x.status === 'Preparing') },
  { status: 'Ready', label: 'Ready to hand over', tickets: tickets.value.filter((x) => x.status === 'Ready') },
])

const avgText = computed(() => {
  if (!avgSeconds.value) return ''
  const mins = Math.round(avgSeconds.value / 60)
  return mins < 1 ? t('under a minute') : t('{n} min', { n: mins })
})

function serverTime(value) {
  if (!value) return 0
  return new Date(String(value).replace(' ', 'T').split('.')[0] + 'Z').getTime()
}

function ageSeconds(ticket) {
  const from = ticket.status === 'Ready' ? ticket.ready_at : ticket.created_at
  return Math.max(0, Math.round((now.value - clockSkew - serverTime(from)) / 1000))
}

function ageText(ticket) {
  const s = ageSeconds(ticket)
  const m = Math.floor(s / 60)
  const text = `${m}:${String(s % 60).padStart(2, '0')}`
  return ticket.status === 'Ready' ? t('ready {t}', { t: text }) : text
}

function ageClass(ticket) {
  if (ticket.status === 'Ready') return 'ok'
  const m = ageSeconds(ticket) / 60
  return m >= 10 ? 'late' : m >= 5 ? 'warn' : 'ok'
}

async function load() {
  if (session.offline) {
    loading.value = false
    return
  }
  try {
    const data = await call('lumen_restaurants.api.kitchen.board', { pos_profile: session.posProfile, station: 'Kitchen' })
    tickets.value = data.tickets || []
    avgSeconds.value = data.avg_seconds || 0
    if (data.now) clockSkew = Date.now() - serverTime(data.now)
  } catch (e) {
    session.notify(e.message, true)
  } finally {
    loading.value = false
  }
}

async function advance(ticket, status) {
  try {
    await call('lumen_restaurants.api.kitchen.set_ticket_status', { name: ticket.name, status })
    await load()
  } catch (e) {
    session.notify(e.message, true)
  }
}

async function printSlip(ticket) {
  try {
    await call('lumen_restaurants.api.printing.print_kitchen_ticket', { ticket: ticket.name })
    session.notify(t('Slip sent to the kitchen printer'))
  } catch (e) {
    session.notify(e.message, true)
  }
}

onMounted(() => {
  load()
  poll = setInterval(load, 5000)
  ticker = setInterval(() => (now.value = Date.now()), 1000)
})
onUnmounted(() => {
  clearInterval(poll)
  clearInterval(ticker)
})
</script>

<style scoped>
.kds { flex: 1; display: flex; padding: 14px; overflow: hidden; }
.kds-card { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.kds-head { display: flex; align-items: center; gap: 10px; padding: 12px 14px; border-bottom: 1px solid var(--border); flex-wrap: wrap; }
.kds-title { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 15px; margin-inline-end: auto; }
.kpill { background: var(--surface-2); border-radius: 999px; padding: 4px 13px; font-size: 12.5px; color: var(--text-muted); }
.kcols { flex: 1; overflow: auto; display: grid; grid-template-columns: repeat(3, minmax(240px, 1fr)); gap: 12px; padding: 14px; background: var(--page-bg); align-content: start; }
.kcol h3 { font-size: 13.5px; margin: 0 4px 10px; color: var(--text-muted); display: flex; align-items: center; gap: 8px; }
.kcount { background: var(--card-bg); border: 1px solid var(--border); border-radius: 999px; padding: 0 10px; font-size: 12px; }
.kempty { padding: 26px 10px; text-align: center; }
.kticket {
  background: var(--card-bg); border: 1px solid var(--border); border-top: 4px solid var(--brand);
  border-radius: 12px; padding: 12px; margin-bottom: 12px; box-shadow: var(--shadow);
}
.kticket.prep { border-top-color: var(--amber); }
.kticket.ready { border-top-color: var(--brand); }
.khead { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
.kno { font-size: 24px; font-weight: 700; line-height: 1; }
.kno.table { font-size: 16px; }
.kbadge { font-size: 11px; font-weight: 700; border-radius: 6px; padding: 1px 8px; }
.kbadge.away { background: rgba(20, 99, 255, 0.1); color: var(--brand-dark); }
.kbadge.hall { background: rgba(109, 74, 255, 0.12); color: var(--promo); }
.ktimer { margin-inline-start: auto; font-size: 12px; font-weight: 700; border-radius: 999px; padding: 2px 10px; }
.ktimer.ok { background: rgba(20, 99, 255, 0.12); color: var(--brand-dark); }
.ktimer.warn { background: rgba(201, 130, 27, 0.15); color: var(--amber); }
.ktimer.late { background: rgba(214, 69, 69, 0.13); color: var(--red); }
.kitems { margin: 0; padding: 0; list-style: none; font-size: 14.5px; }
.kitems li { padding: 4px 0; border-bottom: 1px dashed var(--border-subtle); }
.kitems li:last-child { border: 0; }
.kitems b { display: inline-block; min-width: 32px; }
.knote { display: inline-block; background: rgba(201, 130, 27, 0.14); color: var(--amber); border-radius: 6px; padding: 0 8px; font-size: 12px; margin-inline-start: 6px; }
.kmods { display: flex; flex-wrap: wrap; gap: 4px; margin: 5px 0 2px; padding-inline-start: 32px; }
.kmod { border-radius: 7px; padding: 2px 8px; font-size: 12.5px; font-weight: 700; background: var(--surface-2); color: var(--text); }
.kmod.no { background: color-mix(in srgb, var(--red) 14%, transparent); color: var(--red); }
.kmod.heat { background: color-mix(in srgb, var(--amber) 16%, transparent); color: var(--amber); }
.kmod.cook { background: color-mix(in srgb, var(--promo) 14%, transparent); color: var(--promo); }
.kmod.add { background: color-mix(in srgb, var(--brand) 12%, transparent); color: var(--brand-dark); }
.kfree { margin-top: 4px; }
.kbtns { display: flex; gap: 8px; margin-top: 9px; }
.kbtn { flex: 1; border: 0; border-radius: 10px; padding: 10px; font: inherit; font-weight: 700; font-size: 13.5px; cursor: pointer; }
.kbtn.go { background: var(--brand); color: #fff; }
.kbtn.done { background: var(--brand); color: #fff; }
.kbtn.hand { background: transparent; border: 1.5px solid var(--brand); color: var(--brand-dark); }
.kbtn.print { flex: none; width: 44px; background: var(--surface-2); color: var(--text-muted); }
.kready-note { text-align: center; font-size: 12.5px; color: var(--brand-dark); font-weight: 700; margin-top: 7px; }
@media (max-width: 900px) { .kcols { grid-template-columns: 1fr; } }
</style>
