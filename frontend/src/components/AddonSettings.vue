<!-- Copyright (c) 2026 Lumen Solutions
     SPDX-License-Identifier: AGPL-3.0-only
     "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md. -->
<!-- Lumen Restaurants: an outlet's three add-on switches, in Settings, General,
     Restaurant. They live on the POS Profile (lumen_restaurants.api.menu,
     save_outlet_options, a manager's call). -->
<template>
  <div class="addon-settings lr-settings">
    <div class="sub-label">{{ t('Add-ons on dishes') }}</div>
    <div class="setting-list">
      <label class="setting-row">
        <input v-model="form.enabled" type="checkbox" class="setting-toggle" :disabled="saving" @change="save" />
        <span class="setting-text">
          <span class="setting-title">{{ t('Switch add-ons on') }}</span>
          <span class="setting-desc">{{ t('The add-ons window at the till and the Add-ons tab of the Menu page. Off: a line takes a free note only, as before.') }}</span>
        </span>
      </label>
      <label v-if="form.enabled" class="setting-row">
        <input v-model="form.open_on_tap" type="checkbox" class="setting-toggle" :disabled="saving" @change="save" />
        <span class="setting-text">
          <span class="setting-title">{{ t('Open the add-ons when a dish is tapped') }}</span>
          <span class="setting-desc">{{ t('Off: a tap adds the dish straight away and the cashier taps its line to choose. A dish with a required group always opens its window.') }}</span>
        </span>
      </label>
      <label v-if="form.enabled" class="setting-row">
        <input v-model="form.free_on_receipt" type="checkbox" class="setting-toggle" :disabled="saving" @change="save" />
        <span class="setting-text">
          <span class="setting-title">{{ t('Print the free choices on the customer receipt') }}</span>
          <span class="setting-desc">{{ t('Like no pickles. Paid add-ons always print, with their price.') }}</span>
        </span>
      </label>
    </div>
    <p class="muted hint-row">
      {{ t('The dishes and their add-ons are set up on the Menu page, for the people allowed to edit the menu (Permissions, Edit the menu).') }}
      <button v-if="session.permissions.can_edit_menu" class="btn btn-outline btn-inline" @click="$router.push('/menu')">{{ t('Open the Menu page') }}</button>
    </p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import './restaurant-settings.css'
import { call } from '../api'
import { useSessionStore } from '../stores/session'
import { useModifierStore } from '../stores/modifiers'
import { t } from '../i18n'

const session = useSessionStore()
const modifiers = useModifierStore()
const form = ref({ enabled: true, open_on_tap: true, free_on_receipt: true })
const saving = ref(false)

onMounted(async () => {
  try {
    form.value = await call('lumen_restaurants.api.menu.get_outlet_options', { pos_profile: session.posProfile })
  } catch {
    /* a site not migrated yet reads the defaults */
  }
})

async function save() {
  saving.value = true
  try {
    form.value = await call('lumen_restaurants.api.menu.save_outlet_options', {
      pos_profile: session.posProfile,
      options: form.value,
    })
    modifiers.load(true)
    session.notify(t('Saved'))
  } catch (e) {
    session.notify(e.message, true)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.addon-settings { margin-top: 14px; }
.btn-inline { margin-inline-start: 6px; padding: 4px 10px; font-size: 12.5px; }
</style>
