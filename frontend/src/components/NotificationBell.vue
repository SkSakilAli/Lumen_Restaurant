<!-- Copyright (c) 2026 Lumen Solutions
     SPDX-License-Identifier: AGPL-3.0-only
     "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md. -->
<template>
  <div ref="root" class="notification-wrap">
    <button
      class="notification-button"
      type="button"
      :aria-label="t('Notifications')"
      :aria-expanded="open ? 'true' : 'false'"
      :title="t('Notifications')"
      @click="toggle"
    >
      <Icon name="bell" size="18" />
      <span v-if="unreadCount" class="notification-badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
    </button>
    <section v-if="open" class="notification-panel" :aria-label="t('Notifications')">
      <header class="notification-head">
        <strong>{{ t('Notifications') }}</strong>
        <button class="btn-ghost" type="button" :title="t('Refresh')" @click="refresh">
          <Icon name="refresh" />
        </button>
      </header>
      <div v-if="loading && !items.length" class="notification-empty">{{ t('Loading…') }}</div>
      <div v-else-if="!items.length" class="notification-empty">{{ t('No notifications') }}</div>
      <button
        v-for="item in items"
        :key="item.name"
        class="notification-item"
        :class="{ unread: !item.read_at }"
        type="button"
        @click="openNotification(item)"
      >
        <span class="notification-copy">
          <strong>{{ t(item.subject) }}</strong>
          <span v-if="item.message">{{ item.message }}</span>
          <small>{{ time(item.creation) }}<span v-if="item.pos_profile"> · {{ item.pos_profile }}</span></small>
        </span>
        <span v-if="!item.read_at" class="unread-dot" />
      </button>
    </section>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { call } from '../api'
import Icon from './Icon.vue'
import { useSessionStore } from '../stores/session'
import { t } from '../i18n'
import { connectRealtime } from '../realtime'

const session = useSessionStore()
const router = useRouter()
const root = ref(null)
const open = ref(false)
const loading = ref(false)
const items = ref([])
const unreadCount = ref(0)
const announced = new Set()
let socket = null
let poll = null

async function refresh(eventName = null) {
  if (typeof eventName !== 'string') eventName = null
  if (session.offline) return
  loading.value = true
  try {
    const result = await call('lumen_restaurants.api.notifications.list_notifications')
    items.value = result.items || []
    unreadCount.value = result.unread_count || 0
    if (eventName && !announced.has(eventName)) {
      const item = items.value.find((row) => row.name === eventName)
      if (item && !item.read_at) {
        announced.add(eventName)
        session.notify(`${t(item.subject)}${item.message ? `: ${item.message}` : ''}`)
      }
    }
  } catch (error) {
    if (!session.offline) console.error('Could not refresh POS notifications', error)
  } finally {
    loading.value = false
  }
}

function onRealtimeNotification(data) {
  if (data?.name) refresh(data.name)
  else refresh()
}

function time(value) {
  return String(value || '').split(' ')[1]?.slice(0, 5) || ''
}

function toggle() {
  open.value = !open.value
  if (open.value) refresh()
}

async function openNotification(item) {
  try {
    if (!item.read_at) {
      await call('lumen_restaurants.api.notifications.mark_read', { name: item.name })
      item.read_at = new Date().toISOString()
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    }
    open.value = false
    if (item.route?.startsWith('/') && !item.route.startsWith('//')) {
      await router.push(item.route)
    }
  } catch (error) {
    session.notify(error.message, true)
  }
}

function closeOutside(event) {
  if (open.value && root.value && !root.value.contains(event.target)) open.value = false
}

onMounted(async () => {
  await refresh()
  poll = setInterval(refresh, 15000)
  window.addEventListener('focus', refresh)
  window.addEventListener('pointerdown', closeOutside)
  try {
    socket = await connectRealtime()
    socket.on('lumenpos_notification', onRealtimeNotification)
    socket.on('connect', refresh)
    socket.once('connect_error', (error) => {
      console.warn('Could not connect to POS realtime notifications; using refresh fallback', error)
    })
  } catch (error) {
    console.warn('POS realtime notifications are unavailable; using refresh fallback', error)
  }
})

onBeforeUnmount(() => {
  clearInterval(poll)
  window.removeEventListener('focus', refresh)
  window.removeEventListener('pointerdown', closeOutside)
  if (socket) socket.disconnect()
})
</script>

<style scoped>
.notification-wrap { position: relative; }
.notification-button {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  color: #fff;
  background: rgba(255, 255, 255, 0.16);
  border-radius: 999px;
  cursor: pointer;
}
.notification-button:hover { background: rgba(255, 255, 255, 0.26); }
.notification-badge {
  position: absolute;
  top: -4px;
  inset-inline-end: -5px;
  min-width: 17px;
  padding: 1px 4px;
  border-radius: 999px;
  background: #e23b3b;
  color: #fff;
  font-size: 10px;
  font-weight: 800;
  line-height: 15px;
}
.notification-panel {
  position: absolute;
  z-index: 80;
  top: calc(100% + 9px);
  inset-inline-end: 0;
  width: min(360px, calc(100vw - 24px));
  max-height: min(70vh, 520px);
  overflow-y: auto;
  color: var(--text);
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.22);
}
.notification-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
}
.notification-head strong { font-size: 14px; }
.notification-empty { padding: 24px 12px; color: var(--text-muted); text-align: center; }
.notification-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 12px;
  color: inherit;
  background: transparent;
  border-bottom: 1px solid var(--border-subtle);
  text-align: start;
  cursor: pointer;
}
.notification-item:hover { background: var(--surface-2); }
.notification-item.unread { background: color-mix(in srgb, var(--brand) 7%, transparent); }
.notification-copy { display: flex; flex: 1; flex-direction: column; gap: 3px; min-width: 0; }
.notification-copy strong { font-size: 13px; }
.notification-copy > span { color: var(--text-muted); font-size: 12px; overflow-wrap: anywhere; }
.notification-copy small { color: var(--text-muted); font-size: 10.5px; }
.unread-dot { width: 8px; height: 8px; flex: none; border-radius: 50%; background: var(--brand); }
</style>
