<!-- Copyright (c) 2026 Lumen Solutions
     SPDX-License-Identifier: AGPL-3.0-only
     Lumen Restaurants 0.1.0-r14: "Right now", beside the floor plan while no
     table is picked: how full the place is, what is open, who has sat the
     longest, and today's bookings still to come. -->
<template>
  <div class="p-head"><span class="p-title">{{ t('Right now') }}</span></div>
  <div class="p-body">
    <div class="meta">
      <div>
        <small>{{ t('Tables with an order') }}</small>
        <b><bdi>{{ stats.busy }} / {{ stats.total }}</bdi></b>
      </div>
      <div><small>{{ t('Guests now') }}</small><b>{{ stats.guests }}</b></div>
      <div><small>{{ t('Open orders value') }}</small><b>{{ money(stats.value) }}</b></div>
      <div>
        <small>{{ t('Longest sitting') }}</small>
        <b>{{ stats.longest ? stats.longest.text : '0' }}</b>
        <em v-if="stats.longest">{{ t('Table {no}', { no: stats.longest.table_no }) }}</em>
      </div>
    </div>
    <div class="sec">
      <div class="sec-title">{{ t('Coming bookings') }}</div>
      <div v-if="upcoming.length" class="rows">
        <button v-for="b in upcoming" :key="b.name" type="button" class="row-btn" @click="$emit('goto', b)">
          <span class="rb-time">{{ clockOf(b.time, t) }}</span>
          <span class="rb-main">
            {{ b.table_no ? t('Table {no}', { no: b.table_no }) : t('Not at a table') }}
            <small>{{ b.place }}</small>
          </span>
          <span class="rb-side">{{ t('{n} guests', { n: b.guests }) }}</span>
        </button>
      </div>
      <p v-else class="hint">{{ t('No bookings coming up') }}</p>
    </div>
    <p class="hint">{{ t('Tap any table to see its order and act on it.') }}</p>
  </div>
</template>

<script setup>
import { t } from '../i18n'
import { money } from '../format'
import { clockOf } from './plan'

defineProps({
  // { busy, total, guests, value, longest: { text, table_no } | null }
  stats: { type: Object, required: true },
  // [{ name, time, guests, table, table_no, place }]
  upcoming: { type: Array, required: true },
})
defineEmits(['goto'])
</script>
