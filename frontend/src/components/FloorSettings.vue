<!-- Copyright (c) 2026 Lumen Solutions
     SPDX-License-Identifier: AGPL-3.0-only
     "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
     Lumen Restaurants 0.1.0-r14: an outlet's floor plan switch, in Settings,
     General, Restaurant. It lives on the POS Profile (lumen_restaurants.api.floor,
     save_outlet_options, a manager's call). Who may edit the plan is its own
     permission, Edit the floor plan. -->
<template>
  <div class="floor-settings lr-settings">
    <div class="sub-label">{{ t('Floor plan') }}</div>
    <div class="setting-list">
      <label class="setting-row">
        <input v-model="form.floor_plan" type="checkbox" class="setting-toggle" :disabled="saving" @change="save" />
        <span class="setting-text">
          <span class="setting-title">{{ t('Show the tables as a floor plan') }}</span>
          <span class="setting-desc">{{ t('On: the Tables screen draws the plan and the list stays available. Off: the list only.') }}</span>
        </span>
      </label>
    </div>
    <p class="muted hint-row">
      {{ t('Editing the plan is its own permission, managers only by default.') }}
      {{ t('Give it to a role or a person under Permissions, Edit the floor plan.') }}
    </p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import './restaurant-settings.css'
import { call } from '../api'
import { useSessionStore } from '../stores/session'
import { t } from '../i18n'

const session = useSessionStore()
const form = ref({ floor_plan: true })
const saving = ref(false)

onMounted(async () => {
  try {
    form.value = await call('lumen_restaurants.api.floor.get_outlet_options', { pos_profile: session.posProfile })
  } catch {
    /* a site not migrated yet reads the default */
  }
})

async function save() {
  saving.value = true
  try {
    form.value = await call('lumen_restaurants.api.floor.save_outlet_options', {
      pos_profile: session.posProfile,
      options: form.value,
    })
    session.notify(t('Saved'))
  } catch (e) {
    session.notify(e.message, true)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.floor-settings { margin-top: 14px; }
</style>
