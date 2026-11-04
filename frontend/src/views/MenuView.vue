<!-- Copyright (c) 2026 Lumen Solutions
     SPDX-License-Identifier: AGPL-3.0-only
     "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md. -->
<!-- Lumen Restaurants: the Menu page. Dishes (ERPNext items with their price in
     the outlet's price list) and their add-on groups, in one place, for the
     people a restaurant allows to edit the menu (lumen_restaurants.api.menu,
     which checks every call). Built for a big menu: every list that can grow
     has a search, and many dishes can be picked and tied at once. -->
<template>
  <div class="mnu">
    <div class="card mnu-card">
      <div class="mnu-head">
        <div class="mh-title">
          <svg viewBox="0 0 24 24" class="mh-ico" aria-hidden="true"><path d="M5 3.5h11.5A2.5 2.5 0 0 1 19 6v14.5H7.5A2.5 2.5 0 0 1 5 18V3.5Z M9 8.5h6M9 12h6M9 15.5h3.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" /></svg>
          {{ t('Menu') }}
        </div>
        <div v-if="data" class="seg" role="group">
          <button :aria-pressed="tab === 'dishes'" @click="tab = 'dishes'">{{ t('Dishes') }}</button>
          <button v-if="data.options.enabled" :aria-pressed="tab === 'groups'" @click="tab = 'groups'">{{ t('Add-ons') }}</button>
          <button :aria-pressed="tab === 'stations'" @click="openStationsTab">{{ t('Stations') }}</button>
        </div>
        <span class="mh-space" />
        <template v-if="data">
          <button v-if="tab === 'dishes'" class="btn btn-primary" @click="newDish"><Icon name="plus" /> {{ t('New dish') }}</button>
          <button v-else-if="tab === 'groups'" class="btn btn-primary" @click="newGroup"><Icon name="plus" /> {{ t('New group') }}</button>
        </template>
      </div>

      <div class="mnu-body">
        <div v-if="loading && !data" class="mempty muted">{{ t('Loading…') }}</div>
        <div v-else-if="error" class="mempty">
          <Icon name="shield" /> <b>{{ error }}</b>
        </div>
        <template v-else-if="data">
          <div class="mbanner">
            <Icon name="shield" />
            <span>{{ t('Only the people allowed to edit the menu see this page. A manager names them in Settings, Permissions, Edit the menu.') }}</span>
          </div>
          <div v-if="!data.options.enabled" class="mbanner amber">
            <Icon name="warning" />
            <span>{{ t('Add-ons are off at this outlet (Settings, General, Restaurant). The dishes can still be changed here.') }}</span>
          </div>

          <!-- ======================= dishes ======================= -->
          <template v-if="tab === 'dishes'">
            <form v-if="dishForm" class="mform" @submit.prevent="saveDish">
              <h3>{{ dishForm.item_code ? t('Change the dish') : t('New dish') }}</h3>
              <div class="mgrid">
                <label class="mfield wide">
                  <span>{{ t('Dish name') }}</span>
                  <input ref="dishName" v-model="dishForm.item_name" :placeholder="t('For example: Double cheese burger')" autocomplete="off" />
                </label>
                <label class="mfield">
                  <span>{{ t('Price as the till shows it') }}</span>
                  <input v-model="dishForm.price" type="number" min="0" step="0.01" inputmode="decimal" class="num" />
                </label>
                <label class="mfield">
                  <span>{{ t('Section') }}</span>
                  <select v-if="dishForm.newSection === null" :value="dishForm.item_group" @change="pickSection($event.target.value)">
                    <template v-for="block in filingBlocks" :key="block.section">
                      <optgroup v-if="block.nested" :label="block.section">
                        <option v-for="g in block.groups" :key="g" :value="g">{{ g }}</option>
                      </optgroup>
                      <option v-else :value="block.groups[0]">{{ block.groups[0] }}</option>
                    </template>
                    <option value="__new">+ {{ t('New section') }}</option>
                  </select>
                  <span v-else class="mnew-sec">
                    <input v-model="dishForm.newSection" :placeholder="t('Section name')" autocomplete="off" @keydown.enter.prevent="addSection" />
                    <button type="button" class="btn btn-outline btn-sm" :disabled="busy" @click="addSection">{{ t('Add') }}</button>
                    <button type="button" class="btn-ghost" :aria-label="t('Cancel')" @click="dishForm.newSection = null"><Icon name="close" /></button>
                  </span>
                </label>
              </div>
              <template v-if="data.options.enabled">
                <div class="mfield">
                  <span>{{ t('Add-ons from its section') }}</span>
                  <div class="mtags">
                    <span v-for="g in sectionGroups(dishForm.item_group)" :key="g.name" class="mtag many">{{ g.group_name }}</span>
                    <span v-if="!sectionGroups(dishForm.item_group).length" class="muted small">{{ t('No add-ons are tied to this section') }}</span>
                  </div>
                </div>
                <div class="mfield">
                  <span>{{ t('Other add-ons for this dish') }}</span>
                  <div class="msearch">
                    <Icon name="search" />
                    <input v-model="dishForm.fq" type="search" :placeholder="t('Search the add-on groups')" autocomplete="off" />
                  </div>
                  <div class="mpick">
                    <label v-for="g in otherGroups" :key="g.name" class="mpick-row">
                      <input v-model="dishForm.groups" type="checkbox" :value="g.name" />
                      <span><b>{{ g.group_name }}</b><span class="muted small block">{{ optionsPreview(g) }}</span></span>
                    </label>
                    <div v-if="!otherGroups.length" class="muted small mpad">{{ t('Nothing matches that name') }}</div>
                  </div>
                </div>
              </template>
              <div class="mform-foot">
                <button type="button" class="btn btn-outline" @click="dishForm = null">{{ t('Cancel') }}</button>
                <button type="submit" class="btn btn-primary" :disabled="busy">{{ t('Save') }}</button>
              </div>
            </form>

            <div class="mtools">
              <div class="msearch grow">
                <Icon name="search" />
                <input v-model="q" type="search" :placeholder="t('Search for a dish')" autocomplete="off" />
              </div>
              <select v-model="section" class="msel" :aria-label="t('Section')">
                <option value="all">{{ t('All sections') }} ({{ data.dishes.length }})</option>
                <option v-for="s in data.sections" :key="s" :value="s">{{ s }} ({{ countIn(s) }})</option>
              </select>
            </div>

            <div v-if="selectedCodes.length" class="mbulk">
              <b>{{ t('Selected: {n}', { n: selectedCodes.length }) }}</b>
              <template v-if="data.options.enabled && data.groups.length">
                <select v-model="bulkGroup" class="msel" :aria-label="t('Choose an add-on group')">
                  <option value="">{{ t('Choose an add-on group') }}</option>
                  <option v-for="g in data.groups" :key="g.name" :value="g.name">{{ g.group_name }}</option>
                </select>
                <button class="btn btn-primary btn-sm" :disabled="busy" @click="bulkTie(1)">{{ t('Tie') }}</button>
                <button class="btn btn-outline btn-sm" :disabled="busy" @click="bulkTie(0)">{{ t('Untie') }}</button>
              </template>
              <span class="mh-space" />
              <button class="btn btn-outline btn-sm" :disabled="busy" @click="setSale(selectedCodes, 0)">{{ t('Take off sale') }}</button>
              <button class="btn btn-outline btn-sm" :disabled="busy" @click="setSale(selectedCodes, 1)">{{ t('Put on sale') }}</button>
              <button class="btn-ghost" @click="selected = {}">{{ t('Clear the selection') }}</button>
            </div>

            <label class="mlist-head">
              <input ref="allBox" type="checkbox" :checked="allShownPicked" :disabled="!shownDishes.length" @change="pickAllShown($event.target.checked)" />
              <span>{{ t('Select everything shown') }}</span>
              <span class="muted small">{{ t('Shown: {n}', { n: shownDishes.length }) }}</span>
            </label>
            <div v-if="!shownDishes.length" class="mempty muted">{{ t('Nothing matches that name') }}</div>
            <template v-for="block in dishBlocks" :key="block.section">
              <div v-if="block.heading" class="msec-head">
                <span>{{ block.section }}</span>
                <span class="muted small">{{ t('Dishes: {n}', { n: block.dishes.length }) }}</span>
              </div>
              <div class="mlist">
                <div v-for="d in block.dishes" :key="d.item_code" class="mrow" :class="{ picked: selected[d.item_code], off: !d.on_sale }">
                  <input type="checkbox" :checked="Boolean(selected[d.item_code])" :aria-label="t('Select {n}', { n: d.item_name })" @change="pick(d.item_code, $event.target.checked)" />
                  <span class="mph">
                    <img v-if="d.image" :src="d.image" loading="lazy" alt="" />
                    <template v-else>{{ (d.item_name || '?').trim().charAt(0) }}</template>
                  </span>
                  <button class="mrow-main" @click="editDish(d)">
                    <b>{{ d.item_name }}</b>
                    <span class="muted small">{{ d.section === d.item_group ? d.item_group : d.section + ' / ' + d.item_group }}</span>
                    <span v-if="data.options.enabled" class="mtags">
                      <span v-for="g in groupsForDish(d).slice(0, 4)" :key="g.name" class="mtag">{{ g.group_name }}</span>
                      <span v-if="groupsForDish(d).length > 4" class="mtag">+{{ groupsForDish(d).length - 4 }}</span>
                      <span v-if="!groupsForDish(d).length" class="mtag">{{ t('No add-ons') }}</span>
                    </span>
                  </button>
                  <span class="mprice">{{ d.price ? money(d.price) : t('No price') }}</span>
                  <button
                    class="mswitch"
                    role="switch"
                    :aria-checked="d.on_sale ? 'true' : 'false'"
                    :aria-label="t('On sale at the till')"
                    :title="t('On sale at the till')"
                    :disabled="busy"
                    @click="setSale([d.item_code], d.on_sale ? 0 : 1)"
                  />
                </div>
              </div>
            </template>
          </template>

          <!-- ======================= stations ======================= -->
          <template v-else-if="tab === 'stations'">
            <div class="mtools">
              <div class="msearch grow">
                <Icon name="search" />
                <input v-model="stationQuery" type="search" :placeholder="t('Search categories…')" autocomplete="off" />
              </div>
            </div>
            <div v-if="loadingStations" class="mempty muted">{{ t('Loading…') }}</div>
            <div v-else-if="!filteredStations.length" class="mempty muted">{{ t('No categories found') }}</div>
            <div v-else class="mstation-list">
              <div v-for="cat in filteredStations" :key="cat.name" class="mstation-row card">
                <div class="mstation-info">
                  <b>{{ cat.name }}</b>
                  <span v-if="cat.parent_item_group && cat.parent_item_group !== cat.name" class="muted small block">{{ cat.parent_item_group }}</span>
                </div>
                <div class="mstation-acts">
                  <div class="seg" role="group">
                    <button
                      type="button"
                      :aria-pressed="cat.station !== 'Bar'"
                      @click="updateCategoryStation(cat, 'Kitchen')"
                    >
                      🍳 {{ t('Kitchen') }}
                    </button>
                    <button
                      type="button"
                      :aria-pressed="cat.station === 'Bar'"
                      @click="updateCategoryStation(cat, 'Bar')"
                    >
                      🍸 {{ t('Bar') }}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </template>

          <!-- ======================= add-on groups ======================= -->
          <template v-else>
            <div class="mtools">
              <div class="msearch grow">
                <Icon name="search" />
                <input v-model="gq" type="search" :placeholder="t('Search for a group or a choice')" autocomplete="off" />
              </div>
            </div>
            <div v-if="!shownGroups.length" class="mempty muted">
              {{ data.groups.length ? t('Nothing matches that name') : t('No add-on groups yet. Make the first one: Heat level, Without, Sauces.') }}
            </div>
            <div class="mgroups">
              <div v-for="g in shownGroups" :key="g.name" class="mgroup" :class="{ off: g.disabled }">
                <div class="mg-top">
                  <b>{{ g.group_name }}</b>
                  <span class="mtag" :class="g.multiple ? 'many' : 'one'">{{ g.multiple ? t('Several choices') : t('One choice') }}</span>
                  <span v-if="g.required" class="mtag req">{{ t('Required') }}</span>
                  <span v-if="g.disabled" class="mtag">{{ t('Disabled') }}</span>
                </div>
                <div class="small"><span class="muted">{{ t('Choices') }}:</span> {{ optionsPreview(g) }}</div>
                <div class="small mg-sum"><span class="muted">{{ t('Shown with') }}:</span> {{ tieSummary(g) }}</div>
                <div class="mg-acts">
                  <button class="btn btn-outline btn-sm" @click="openTie(g)">
                    <svg viewBox="0 0 24 24" class="bico" aria-hidden="true"><path d="M10 14a4.5 4.5 0 0 0 6.4 0l3-3a4.5 4.5 0 0 0-6.4-6.4l-1 1M14 10a4.5 4.5 0 0 0-6.4 0l-3 3a4.5 4.5 0 0 0 6.4 6.4l1-1" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" /></svg>
                    {{ t('Tie to dishes') }}
                  </button>
                  <button class="btn-ghost" @click="editGroup(g)">{{ t('Edit the choices') }}</button>
                </div>
              </div>
            </div>
          </template>
        </template>
      </div>
    </div>

    <!-- ======================= a group's editor ======================= -->
    <div v-if="groupForm" class="msheet-back" @click.self="groupForm = null">
      <form class="msheet" role="dialog" aria-modal="true" :aria-label="t('Add-on group')" @submit.prevent="saveGroup">
        <header class="msheet-head">
          <b>{{ groupForm.name ? t('Change the group') : t('New group') }}</b>
          <button type="button" class="ms-x" :aria-label="t('Close')" @click="groupForm = null"><Icon name="close" /></button>
        </header>
        <div class="msheet-body">
          <label class="mfield">
            <span>{{ t('Group name') }}</span>
            <input ref="groupName" v-model="groupForm.group_name" :placeholder="t('For example: Heat level')" autocomplete="off" />
          </label>
          <div class="mrules">
            <div class="seg" role="group">
              <button type="button" :aria-pressed="!groupForm.multiple" @click="groupForm.multiple = 0">{{ t('One choice') }}</button>
              <button type="button" :aria-pressed="Boolean(groupForm.multiple)" @click="groupForm.multiple = 1">{{ t('Several choices') }}</button>
            </div>
            <label class="minline"><input v-model="groupForm.required" type="checkbox" :true-value="1" :false-value="0" /> {{ t('Required') }}</label>
            <label v-if="groupForm.multiple" class="minline">
              {{ t('At most') }}
              <select v-model.number="groupForm.max_choices">
                <option :value="0">{{ t('No limit') }}</option>
                <option v-for="n in 6" :key="n" :value="n">{{ n }}</option>
              </select>
            </label>
          </div>
          <div class="mrules">
            <label class="minline">
              {{ t('On the kitchen screen') }}
              <select v-model="groupForm.kitchen_style">
                <option value="Normal">{{ t('As it is') }}</option>
                <option value="Without">{{ t('Without, in red') }}</option>
                <option value="Heat">{{ t('Heat, in amber') }}</option>
                <option value="Cooking">{{ t('Doneness, in violet') }}</option>
              </select>
            </label>
            <label class="minline"><input v-model="groupForm.print_default" type="checkbox" :true-value="1" :false-value="0" /> {{ t('Show the default to the kitchen') }}</label>
            <label class="minline"><input v-model="groupForm.disabled" type="checkbox" :true-value="1" :false-value="0" /> {{ t('Disabled') }}</label>
          </div>
          <div class="mfield">
            <span>{{ t('Choices') }}</span>
            <div class="mopts">
              <div class="mopt head muted small">
                <span>{{ t('Choice') }}</span><span>{{ t('Price') }}</span><span>{{ t('Default') }}</span><span />
              </div>
              <div v-for="(o, i) in groupForm.options" :key="i" class="mopt">
                <input v-model="o.option_name" :placeholder="t('For example: No pickles')" :aria-label="t('Choice')" autocomplete="off" />
                <input v-model="o.price" type="number" min="0" step="0.01" inputmode="decimal" class="num" :placeholder="t('0 is free')" :aria-label="t('Price')" />
                <input type="checkbox" :checked="Boolean(o.is_default)" :aria-label="t('Default')" @change="setDefault(i, $event.target.checked)" />
                <button type="button" class="btn-ghost" :aria-label="t('Remove the row')" :disabled="groupForm.options.length < 2" @click="groupForm.options.splice(i, 1)"><Icon name="close" /></button>
              </div>
            </div>
            <button type="button" class="btn-ghost madd" @click="addOption"><Icon name="plus" /> {{ t('Another choice') }}</button>
            <p class="muted small mhint">{{ t('A choice with a price is billed on its own line under the dish. A choice at 0 is a free instruction for the kitchen.') }}</p>
          </div>
        </div>
        <footer class="msheet-foot">
          <template v-if="groupForm.name">
            <button v-if="!confirmDelete" type="button" class="mdanger" @click="confirmDelete = true">{{ t('Delete the group') }}</button>
            <button v-else type="button" class="mdanger strong" :disabled="busy" @click="deleteGroup">{{ t('Yes, delete it') }}</button>
          </template>
          <span class="mh-space" />
          <span v-if="!groupForm.name" class="muted small">{{ t('After saving you choose the dishes it shows with.') }}</span>
          <button type="button" class="btn btn-outline" @click="groupForm = null">{{ t('Cancel') }}</button>
          <button type="submit" class="btn btn-primary" :disabled="busy">{{ t('Save') }}</button>
        </footer>
      </form>
    </div>

    <!-- ======================= tying a group to dishes ======================= -->
    <div v-if="tie" class="msheet-back" @click.self="tie = null">
      <div class="msheet wide" role="dialog" aria-modal="true" :aria-label="t('Tie the group: {g}', { g: tie.group.group_name })">
        <header class="msheet-head">
          <div class="grow">
            <b>{{ t('Tie the group: {g}', { g: tie.group.group_name }) }}</b>
            <span class="muted small block">{{ t('Tied: {n} of {m}', { n: tiedCount, m: data.dishes.length }) }}</span>
          </div>
          <button class="ms-x" :aria-label="t('Close')" @click="tie = null"><Icon name="close" /></button>
        </header>
        <div class="msheet-body">
          <div class="msearch">
            <Icon name="search" />
            <input ref="tieSearch" v-model="tie.q" type="search" :placeholder="t('Search for a section or a dish')" autocomplete="off" />
          </div>
          <div class="mtie-acts">
            <button class="btn btn-outline btn-sm" @click="tieShown(true)">{{ t('Select all') }}</button>
            <button class="btn btn-outline btn-sm" @click="tieShown(false)">{{ t('Clear all') }}</button>
            <label class="minline end"><input v-model="tie.only" type="checkbox" /> {{ t('Tied only') }}</label>
          </div>
          <div class="mtree">
            <template v-for="v in tieView" :key="v.section">
              <div class="mtree-sec">
                <label>
                  <input type="checkbox" :checked="v.state === 'all'" :indeterminate.prop="v.state === 'some'" @change="tieSection(v.section)" />
                  <b>{{ v.section }}</b>
                </label>
                <span v-if="tie.cats[v.section]" class="mtag many">{{ t('Whole section') }}</span>
                <span class="muted small num">{{ t('{a} of {b}', { a: v.tied, b: v.dishes.length }) }}</span>
                <button class="mchev" :class="{ open: v.open }" :aria-expanded="v.open ? 'true' : 'false'" :aria-label="t('Show the dishes')" @click="tie.open[v.section] = !tie.open[v.section]">
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 9 6 6 6-6" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" /></svg>
                </button>
              </div>
              <template v-if="v.open">
                <label v-for="d in v.shown" :key="d.item_code" class="mtree-dish">
                  <input type="checkbox" :checked="isTied(d)" @change="tieDish(d)" />
                  <span class="grow">{{ d.item_name }}</span>
                  <span class="muted small">{{ d.price ? money(d.price) : '' }}</span>
                </label>
              </template>
            </template>
            <div v-if="!tieView.length" class="muted small mpad">{{ t('Nothing matches that name') }}</div>
          </div>
        </div>
        <footer class="msheet-foot">
          <span class="muted small grow">{{ t('A whole section includes any dish added to it later.') }}</span>
          <button class="btn btn-outline" @click="tie = null">{{ t('Cancel') }}</button>
          <button class="btn btn-primary" :disabled="busy" @click="saveTie">{{ t('Save') }}</button>
        </footer>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import Icon from '../components/Icon.vue'
import { call } from '../api'
import { useSessionStore } from '../stores/session'
import { useCatalogStore } from '../stores/catalog'
import { useModifierStore } from '../stores/modifiers'
import { money } from '../format'
import { t, locale } from '../i18n'

const session = useSessionStore()
const catalog = useCatalogStore()
const modifiers = useModifierStore()

const data = ref(null)
const loading = ref(true)
const error = ref('')
const busy = ref(false)
const tab = ref('dishes')
const q = ref('')
const section = ref('all')
const selected = ref({})
const bulkGroup = ref('')
const dishForm = ref(null)
const gq = ref('')
const groupForm = ref(null)
const confirmDelete = ref(false)
const tie = ref(null)
const dishName = ref(null)
const groupName = ref(null)
const tieSearch = ref(null)

const stationsList = ref([])
const stationQuery = ref('')
const loadingStations = ref(false)

async function openStationsTab() {
  tab.value = 'stations'
  loadingStations.value = true
  try {
    stationsList.value = await call('lumen_restaurants.api.kitchen.get_station_categories')
  } catch (e) {
    session.notify(e.message, true)
  } finally {
    loadingStations.value = false
  }
}

async function updateCategoryStation(cat, st) {
  try {
    await call('lumen_restaurants.api.kitchen.set_category_station', {
      item_group: cat.name,
      station: st,
    })
    cat.station = st
    session.notify(t('{name} routed to {station}', { name: cat.name, station: st }))
  } catch (e) {
    session.notify(e.message, true)
  }
}

const filteredStations = computed(() => {
  const query = stationQuery.value.trim().toLowerCase()
  if (!query) return stationsList.value
  return stationsList.value.filter(c => (c.name || '').toLowerCase().includes(query))
})
let changed = false

const listSep = computed(() => (locale.value === 'ar' ? '، ' : ', '))

// Search that forgives the usual Arabic spelling differences: a hamza on the
// alef, a ta marbuta, an alef maqsura, the diacritics.
function norm(s) {
  return String(s || '')
    .toLowerCase()
    .replace(/[\u064B-\u0652\u0640]/g, '')
    .replace(/[أإآ]/g, 'ا')
    .replace(/ة/g, 'ه')
    .replace(/ى/g, 'ي')
    .trim()
}
const has = (text, query) => !query || norm(text).includes(query)

async function load() {
  loading.value = true
  try {
    data.value = await call('lumen_restaurants.api.menu.get_menu', { pos_profile: session.posProfile })
    error.value = ''
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function run(method, args, done) {
  busy.value = true
  try {
    const out = await call(`lumen_restaurants.api.menu.${method}`, { pos_profile: session.posProfile, ...args })
    changed = true
    if (done) session.notify(done)
    await load()
    return out
  } catch (e) {
    session.notify(e.message, true)
    return null
  } finally {
    busy.value = false
  }
}

// --- ties ---------------------------------------------------------------
// A tied section covers its sub-sections (the server says which).
function covered(sectionName) {
  return data.value.covers?.[sectionName] || [sectionName]
}
function linkedTo(g, d) {
  return g.dishes.includes(d.item_code) || g.sections.some((s) => covered(s).includes(d.item_group))
}
function groupsForDish(d) {
  return data.value.groups.filter((g) => linkedTo(g, d))
}
function sectionGroups(sectionName) {
  return data.value.groups.filter((g) => g.sections.some((s) => covered(s).includes(sectionName)))
}
function optionsPreview(g) {
  const names = g.options.slice(0, 5).map((o) => (o.price > 0 ? `${o.option_name} +${Number(o.price).toFixed(2)}` : o.option_name))
  return names.join(listSep.value) + (g.options.length > 5 ? ` +${g.options.length - 5}` : '')
}
function tieSummary(g) {
  const count = data.value.dishes.filter((d) => linkedTo(g, d)).length
  if (!count) return t('Not tied to any dish yet')
  const parts = []
  if (g.sections.length) {
    const names = g.sections.slice(0, 3).join(listSep.value) + (g.sections.length > 3 ? ` +${g.sections.length - 3}` : '')
    parts.push(t('Whole sections: {list}', { list: names }))
  }
  const singles = g.dishes.filter((code) => {
    const d = data.value.dishes.find((x) => x.item_code === code)
    return !d || !g.sections.some((s) => covered(s).includes(d.item_group))
  }).length
  if (singles) parts.push(t('Single dishes: {n}', { n: singles }))
  parts.push(t('Dishes: {n}', { n: count }))
  return parts.join(' · ')
}

// --- dishes ---------------------------------------------------------------
function countIn(sectionName) {
  return data.value.dishes.filter((d) => d.section === sectionName).length
}
// The groups a dish can be filed in, under the section that covers them: one
// line each, or an optgroup when a listed section has groups beneath it.
const filingBlocks = computed(() => {
  if (!data.value) return []
  const blocks = []
  for (const s of data.value.sections) {
    const groups = (data.value.filing || []).filter((f) => f.section === s).map((f) => f.name)
    if (groups.length) blocks.push({ section: s, groups, nested: groups.length > 1 || groups[0] !== s })
  }
  return blocks
})
const shownDishes = computed(() => {
  if (!data.value) return []
  const query = norm(q.value)
  return data.value.dishes.filter(
    (d) => (section.value === 'all' || d.section === section.value) && has(d.item_name, query)
  )
})
const dishBlocks = computed(() => {
  const list = shownDishes.value
  if (section.value !== 'all' || norm(q.value)) return list.length ? [{ section: 'all', heading: false, dishes: list }] : []
  return data.value.sections
    .map((s) => ({ section: s, heading: true, dishes: list.filter((d) => d.section === s) }))
    .filter((block) => block.dishes.length)
})
const selectedCodes = computed(() => Object.keys(selected.value).filter((code) => selected.value[code]))
const allShownPicked = computed(
  () => shownDishes.value.length > 0 && shownDishes.value.every((d) => selected.value[d.item_code])
)
function pick(code, on) {
  const next = { ...selected.value }
  if (on) next[code] = true
  else delete next[code]
  selected.value = next
}
function pickAllShown(on) {
  const next = { ...selected.value }
  for (const d of shownDishes.value) {
    if (on) next[d.item_code] = true
    else delete next[d.item_code]
  }
  selected.value = next
}

function newDish() {
  const filing = data.value.filing || []
  const first = (filing.find((f) => section.value !== 'all' && f.section === section.value) || filing[0] || {}).name || ''
  dishForm.value = { item_code: null, item_name: '', price: '', item_group: first, groups: [], fq: '', newSection: null }
  nextTick(() => dishName.value?.focus())
}
function editDish(d) {
  dishForm.value = {
    item_code: d.item_code,
    item_name: d.item_name,
    price: d.price || '',
    item_group: d.item_group,
    groups: data.value.groups.filter((g) => g.dishes.includes(d.item_code)).map((g) => g.name),
    fq: '',
    newSection: null,
  }
  nextTick(() => dishName.value?.focus())
}
const otherGroups = computed(() => {
  if (!dishForm.value || !data.value) return []
  const query = norm(dishForm.value.fq)
  const fromSection = new Set(sectionGroups(dishForm.value.item_group).map((g) => g.name))
  return data.value.groups.filter(
    (g) => !fromSection.has(g.name) && (has(g.group_name, query) || g.options.some((o) => has(o.option_name, query)))
  )
})
function pickSection(value) {
  if (value === '__new') dishForm.value.newSection = ''
  else dishForm.value.item_group = value
}
async function addSection() {
  const name = (dishForm.value.newSection || '').trim()
  if (!name) return
  const out = await run('new_section', { name }, t('Section added'))
  if (out) {
    dishForm.value.item_group = out.name
    dishForm.value.newSection = null
    // the till's section list, without a reload
    // a chip of its own when the outlet shows it as a section (not beneath a listed parent)
    if ((out.sections || []).includes(out.name) && !session.itemGroups.includes(out.name)) session.itemGroups.push(out.name)
  }
}
async function saveDish() {
  const f = dishForm.value
  if (!f.item_name.trim()) return dishName.value?.focus()
  const fromSection = new Set(sectionGroups(f.item_group).map((g) => g.name))
  const out = await run(
    'save_dish',
    {
      dish: {
        item_code: f.item_code,
        item_name: f.item_name,
        price: f.price,
        item_group: f.item_group,
        groups: data.value.options.enabled ? f.groups.filter((g) => !fromSection.has(g)) : undefined,
      },
    },
    f.item_code ? t('Dish saved') : t('Dish added, and it shows at the till straight away')
  )
  if (out) {
    dishForm.value = null
    if (section.value !== 'all' && section.value !== out.section) section.value = out.section
  }
}
async function setSale(codes, onSale) {
  const done = onSale ? t('Put on sale: {n}', { n: codes.length }) : t('Taken off sale: {n}', { n: codes.length })
  await run('set_on_sale', { items: codes, on_sale: onSale }, done)
}
async function bulkTie(on) {
  const g = data.value.groups.find((x) => x.name === bulkGroup.value)
  if (!g) return session.notify(t('Choose the add-on group first'), true)
  const codes = selectedCodes.value
  const done = on
    ? t('{g} tied to the selected dishes: {n}', { g: g.group_name, n: codes.length })
    : t('{g} untied from the selected dishes: {n}', { g: g.group_name, n: codes.length })
  await run('bulk_tie', { name: g.name, items: codes, tie: on }, done)
}

// --- groups ---------------------------------------------------------------
const shownGroups = computed(() => {
  if (!data.value) return []
  const query = norm(gq.value)
  return data.value.groups.filter((g) => has(g.group_name, query) || g.options.some((o) => has(o.option_name, query)))
})
function blankOption() {
  return { id: null, option_name: '', price: '', is_default: 0 }
}
function newGroup() {
  confirmDelete.value = false
  groupForm.value = {
    name: null, group_name: '', multiple: 1, required: 0, max_choices: 0, kitchen_style: 'Normal',
    print_default: 0, disabled: 0, options: [blankOption(), blankOption()],
  }
  nextTick(() => groupName.value?.focus())
}
function editGroup(g) {
  confirmDelete.value = false
  groupForm.value = {
    ...JSON.parse(JSON.stringify(g)),
    options: g.options.map((o) => ({ id: o.id, option_name: o.option_name, price: o.price || '', is_default: o.is_default })),
  }
  nextTick(() => groupName.value?.focus())
}
function addOption() {
  groupForm.value.options.push(blankOption())
}
function setDefault(i, on) {
  const f = groupForm.value
  f.options.forEach((o, j) => {
    if (j === i) o.is_default = on ? 1 : 0
    else if (on && !f.multiple) o.is_default = 0
  })
}
async function saveGroup() {
  const f = groupForm.value
  if (!f.group_name.trim()) return groupName.value?.focus()
  if (!f.options.some((o) => (o.option_name || '').trim())) return session.notify(t('Add at least one choice'), true)
  const isNew = !f.name
  const out = await run('save_group', { group: f }, isNew ? t('Group added, choose the dishes it shows with') : t('Group saved'))
  if (!out) return
  groupForm.value = null
  if (isNew) openTie(data.value.groups.find((g) => g.name === out.name) || out)
}
async function deleteGroup() {
  const f = groupForm.value
  const out = await run('delete_group', { name: f.name }, t('Group deleted'))
  if (out) groupForm.value = null
}

// --- the tie sheet --------------------------------------------------------
function openTie(g) {
  const cats = {}
  const dishes = {}
  for (const s of data.value.sections) {
    if (g.sections.some((x) => covered(x).includes(s))) cats[s] = true
  }
  // A dish tied alone, or through a sub-section tied in ERPNext, shows ticked.
  for (const d of data.value.dishes) {
    if (!cats[d.section] && linkedTo(g, d)) dishes[d.item_code] = true
  }
  const open = {}
  for (const s of data.value.sections) {
    if (data.value.dishes.some((d) => d.section === s && dishes[d.item_code])) open[s] = true
  }
  tie.value = { group: g, cats, dishes, q: '', only: false, open }
  nextTick(() => tieSearch.value?.focus())
}
function isTied(d) {
  return Boolean(tie.value.cats[d.section] || tie.value.dishes[d.item_code])
}
function dishesIn(sectionName) {
  return data.value.dishes.filter((d) => d.section === sectionName)
}
const tieView = computed(() => {
  if (!tie.value) return []
  const query = norm(tie.value.q)
  return data.value.sections
    .map((s) => {
      const all = dishesIn(s)
      const sectionHit = has(s, query)
      let shown = sectionHit ? all : all.filter((d) => has(d.item_name, query))
      if (tie.value.only) shown = shown.filter(isTied)
      const tied = all.filter(isTied).length
      return {
        section: s,
        dishes: all,
        shown,
        sectionHit: sectionHit && !tie.value.only,
        tied,
        state: tied === 0 ? (tie.value.cats[s] ? 'all' : 'none') : tied === all.length ? 'all' : 'some',
        open: Boolean(query || tie.value.only || tie.value.open[s]),
      }
    })
    .filter((v) => v.shown.length || (v.sectionHit && !query && !v.dishes.length))
})
const tiedCount = computed(() => (tie.value ? data.value.dishes.filter(isTied).length : 0))
function tieSection(s) {
  const L = tie.value
  const all = dishesIn(s)
  const whole = L.cats[s] || (all.length && all.every((d) => L.dishes[d.item_code]))
  delete L.cats[s]
  for (const d of all) delete L.dishes[d.item_code]
  if (!whole) L.cats[s] = true
}
function tieDish(d) {
  const L = tie.value
  const all = dishesIn(d.section)
  if (L.cats[d.section]) {
    delete L.cats[d.section]
    for (const x of all) if (x.item_code !== d.item_code) L.dishes[x.item_code] = true
    return
  }
  if (L.dishes[d.item_code]) {
    delete L.dishes[d.item_code]
    return
  }
  L.dishes[d.item_code] = true
  // every dish of the section ticked: the whole section, dishes added later too
  if (all.every((x) => L.dishes[x.item_code])) {
    L.cats[d.section] = true
    for (const x of all) delete L.dishes[x.item_code]
  }
}
function tieShown(on) {
  const L = tie.value
  for (const v of tieView.value) {
    if (v.sectionHit) {
      delete L.cats[v.section]
      for (const d of v.dishes) delete L.dishes[d.item_code]
      if (on) L.cats[v.section] = true
      continue
    }
    for (const d of v.shown) if (isTied(d) !== on) tieDish(d)
  }
}
async function saveTie() {
  const L = tie.value
  // Ties made in ERPNext to a group this outlet does not show (a sub-section,
  // or a parent) stay as they are while every dish they cover is still ticked.
  const listed = new Set(data.value.sections)
  const keep = L.group.sections.filter(
    (s) => !listed.has(s) && data.value.dishes.filter((d) => covered(s).includes(d.item_group)).every(isTied)
  )
  const sections = [...keep, ...data.value.sections.filter((s) => L.cats[s] && !keep.some((k) => covered(k).includes(s)))]
  const items = Object.keys(L.dishes).filter((code) => L.dishes[code])
  const out = await run('tie_group', { name: L.group.name, sections, items }, t('Saved. Dishes: {n}', { n: tiedCount.value }))
  if (out) tie.value = null
}

function onKey(event) {
  if (event.key !== 'Escape') return
  if (tie.value) tie.value = null
  else if (groupForm.value) groupForm.value = null
}

onMounted(() => {
  load()
  window.addEventListener('keydown', onKey)
})
onUnmounted(() => {
  window.removeEventListener('keydown', onKey)
  // The till picks up what changed here: the menu grid and the add-ons.
  if (changed) {
    catalog.cacheFullCatalog()
    modifiers.load(true)
  }
})
</script>

<style scoped>
.mnu { flex: 1; display: flex; padding: 14px; overflow: hidden; }
.mnu-card { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.mnu-head { display: flex; align-items: center; gap: 12px; padding: 12px 14px; border-bottom: 1px solid var(--border); flex-wrap: wrap; }
.mh-title { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 15px; }
.mh-ico { width: 20px; height: 20px; color: var(--brand); }
.mh-space { flex: 1; }
.seg { display: inline-flex; background: var(--surface-2); border-radius: 11px; padding: 3px; gap: 2px; }
.seg button { border: 0; background: transparent; padding: 7px 14px; border-radius: 9px; font: inherit; font-weight: 600; font-size: 13px; color: var(--text-muted); cursor: pointer; }
.seg button[aria-pressed='true'] { background: var(--brand); color: #fff; }
.mnu-body { flex: 1; overflow: auto; padding: 14px; background: var(--page-bg); }
.mempty { padding: 30px 10px; text-align: center; display: flex; gap: 8px; justify-content: center; align-items: center; }
.mbanner { display: flex; gap: 8px; align-items: flex-start; padding: 10px 12px; margin-bottom: 12px; border-radius: 12px; font-size: 13px; background: color-mix(in srgb, var(--promo) 10%, transparent); color: var(--text); }
.mbanner.amber { background: color-mix(in srgb, var(--amber) 14%, transparent); }
.mbanner .icon { color: var(--promo); flex: none; }
.mtools { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-bottom: 10px; }
.grow { flex: 1; min-width: 0; }
.block { display: block; }
.num { font-variant-numeric: tabular-nums; }
.msearch { display: flex; align-items: center; gap: 7px; border: 1px solid var(--border); border-radius: 11px; padding: 0 12px; background: var(--input-bg); min-width: 200px; }
.msearch .icon { color: var(--text-muted); }
.msearch input { flex: 1; min-width: 0; border: 0; background: transparent; padding: 10px 0; font: inherit; font-size: 14px; outline: none; color: var(--text); }
.msel { padding: 9px 10px; border: 1px solid var(--border); border-radius: 10px; font: inherit; font-size: 13.5px; background: var(--input-bg); color: var(--text); max-width: 100%; }
.mbulk { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; padding: 10px 12px; margin-bottom: 10px; border: 1px solid var(--brand); background: color-mix(in srgb, var(--brand) 8%, var(--card-bg)); border-radius: 12px; }
.btn-sm { padding: 6px 12px; font-size: 13px; }
.mlist-head { display: flex; gap: 10px; align-items: center; padding: 2px 12px 8px; font-weight: 700; font-size: 13px; cursor: pointer; }
.mlist-head .muted { font-weight: 500; }
.msec-head { display: flex; justify-content: space-between; gap: 8px; align-items: baseline; margin: 14px 4px 6px; font-weight: 800; }
.mlist { display: flex; flex-direction: column; gap: 7px; }
.mrow { display: grid; grid-template-columns: auto auto minmax(0, 1fr) auto auto; gap: 12px; align-items: center; padding: 9px 12px; background: var(--card-bg); border: 1px solid var(--border); border-radius: 13px; }
.mrow.picked { border-color: var(--brand); box-shadow: inset 0 0 0 1px var(--brand); }
.mrow.off .mrow-main b, .mrow.off .mprice { color: var(--text-muted); text-decoration: line-through; }
.mrow input[type='checkbox'], .mlist-head input, .mpick-row input, .mtree input { width: 18px; height: 18px; accent-color: var(--brand); cursor: pointer; flex: none; }
.mph { width: 42px; height: 42px; border-radius: 11px; display: grid; place-items: center; overflow: hidden; background: rgba(20, 99, 255, 0.1); color: var(--brand-dark); font-weight: 800; }
.mph img { width: 100%; height: 100%; object-fit: cover; }
.mrow-main { border: 0; background: transparent; text-align: start; font: inherit; color: var(--text); cursor: pointer; display: flex; flex-direction: column; gap: 2px; padding: 0; min-width: 0; }
.mrow-main b { font-size: 14px; }
.mprice { font-weight: 800; font-size: 14px; white-space: nowrap; }
.mswitch { position: relative; width: 40px; height: 23px; border-radius: 12px; border: 0; background: var(--border); cursor: pointer; flex: none; }
.mswitch::after { content: ''; position: absolute; top: 3px; inset-inline-start: 3px; width: 17px; height: 17px; border-radius: 50%; background: #fff; transition: inset-inline-start 0.15s; }
.mswitch[aria-checked='true'] { background: var(--brand); }
.mswitch[aria-checked='true']::after { inset-inline-start: 20px; }
.mtags { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 3px; }
.mtag { display: inline-flex; align-items: center; padding: 1px 8px; border-radius: 999px; font-size: 11.5px; font-weight: 700; background: var(--surface-2); color: var(--text-muted); white-space: nowrap; }
.mtag.one { background: color-mix(in srgb, var(--promo) 14%, transparent); color: var(--promo); }
.mtag.many { background: color-mix(in srgb, var(--brand) 12%, transparent); color: var(--brand-dark); }
.mtag.req { background: color-mix(in srgb, var(--amber) 16%, transparent); color: var(--amber); }
.mform { background: var(--card-bg); border: 1.5px solid var(--brand); border-radius: 14px; padding: 14px; margin-bottom: 12px; display: flex; flex-direction: column; gap: 12px; }
.mform h3 { margin: 0; font-size: 15px; }
.mgrid { display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 10px; }
.mfield { display: flex; flex-direction: column; gap: 5px; font-size: 12.5px; font-weight: 700; color: var(--text-muted); min-width: 0; }
.mfield input, .mfield select { padding: 9px 11px; border: 1px solid var(--border); border-radius: 10px; font: inherit; font-size: 14px; font-weight: 500; background: var(--input-bg); color: var(--text); min-width: 0; }
.mnew-sec { display: flex; gap: 6px; align-items: center; }
.mnew-sec input { flex: 1; }
.mpick { max-height: 230px; overflow: auto; border: 1px solid var(--border); border-radius: 10px; padding: 2px 12px; background: var(--input-bg); }
.mpick-row { display: flex; gap: 10px; align-items: flex-start; padding: 8px 0; border-top: 1px solid var(--border-subtle); cursor: pointer; font-weight: 500; color: var(--text); }
.mpick-row:first-child { border-top: 0; }
.mpad { padding: 8px 0; }
.mform-foot { display: flex; gap: 8px; justify-content: flex-end; flex-wrap: wrap; }
.mgroups { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(320px, 100%), 1fr)); gap: 12px; align-items: start; }
.mgroup { background: var(--card-bg); border: 1px solid var(--border); border-radius: 14px; padding: 14px; display: flex; flex-direction: column; gap: 7px; }
.mgroup.off { opacity: 0.7; }
.mg-top { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.mg-top b { flex: 1; min-width: 0; font-size: 15px; }
.mg-sum { line-height: 1.7; }
.mg-acts { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 2px; }
.bico { width: 15px; height: 15px; }
.mstation-list { display: flex; flex-direction: column; gap: 8px; padding: 4px 0; }
.mstation-row { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; border: 1px solid var(--border); border-radius: 12px; gap: 12px; }
.mstation-info { flex: 1; }
.mstation-info b { font-size: 15px; }
.msheet-back { position: fixed; inset: 0; z-index: 60; background: rgba(8, 12, 22, 0.55); display: grid; place-items: center; padding: 16px; }
.msheet { width: min(620px, 100%); max-height: min(90vh, 820px); display: flex; flex-direction: column; background: var(--card-bg); color: var(--text); border-radius: var(--radius-lg); box-shadow: var(--shadow-md); overflow: hidden; }
.msheet.wide { width: min(680px, 100%); }
.msheet-head { display: flex; gap: 12px; align-items: center; padding: 14px 16px; border-bottom: 1px solid var(--border); }
.msheet-head b { font-size: 16px; }
.ms-x { border: 0; background: var(--surface-2); color: var(--text); width: 36px; height: 36px; border-radius: 10px; display: grid; place-items: center; cursor: pointer; margin-inline-start: auto; }
.msheet-body { padding: 12px 16px 14px; overflow: auto; display: flex; flex-direction: column; gap: 12px; }
.msheet-foot { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; padding: 12px 16px; border-top: 1px solid var(--border); }
.mrules { display: flex; flex-wrap: wrap; gap: 10px 16px; align-items: center; font-size: 13px; }
.minline { display: inline-flex; gap: 7px; align-items: center; font-size: 13px; font-weight: 600; cursor: pointer; }
.minline.end { margin-inline-start: auto; }
.minline select { padding: 5px 8px; border: 1px solid var(--border); border-radius: 8px; font: inherit; background: var(--input-bg); color: var(--text); }
.minline input[type='checkbox'] { width: 17px; height: 17px; accent-color: var(--brand); }
.mopts { display: flex; flex-direction: column; gap: 6px; }
.mopt { display: grid; grid-template-columns: minmax(0, 1fr) 110px 54px 36px; gap: 6px; align-items: center; }
.mopt.head { font-weight: 700; }
.mopt input:not([type='checkbox']) { padding: 8px 10px; border: 1px solid var(--border); border-radius: 9px; font: inherit; font-size: 14px; background: var(--input-bg); color: var(--text); min-width: 0; }
.mopt input[type='checkbox'] { width: 18px; height: 18px; accent-color: var(--brand); justify-self: center; }
.madd { align-self: flex-start; }
.mhint { margin: 0; }
.mdanger { border: 0; background: transparent; color: var(--red); font: inherit; font-weight: 700; cursor: pointer; padding: 8px 4px; }
.mdanger.strong { background: var(--red); color: #fff; border-radius: 9px; padding: 8px 12px; }
.mtie-acts { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.mtree { display: flex; flex-direction: column; }
.mtree-sec { display: flex; align-items: center; gap: 8px; padding: 9px 2px; border-top: 1px solid var(--border-subtle); }
.mtree-sec:first-child { border-top: 0; }
.mtree-sec label { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; cursor: pointer; }
.mtree-dish { display: flex; align-items: center; gap: 10px; padding: 6px 2px; padding-inline-start: 30px; font-size: 13.5px; cursor: pointer; }
.mchev { border: 0; background: var(--surface-2); color: var(--text); width: 30px; height: 30px; border-radius: 9px; display: grid; place-items: center; cursor: pointer; }
.mchev svg { width: 16px; height: 16px; transition: transform 0.15s; }
.mchev.open svg { transform: rotate(180deg); }
@media (prefers-reduced-motion: reduce) { .mchev svg, .mswitch::after { transition: none; } }
@media (max-width: 900px) {
  .mgrid { grid-template-columns: 1fr 1fr; }
  .mgrid .wide { grid-column: 1 / -1; }
}
@media (max-width: 720px) {
  .mnu { padding: 8px; }
  .mrow { grid-template-columns: auto minmax(0, 1fr) auto; }
  .mrow .mph { display: none; }
  .mrow .mswitch { grid-column: 3; }
  .mopt { grid-template-columns: minmax(0, 1fr) 84px 44px 32px; }
  .msheet-back { place-items: end center; padding: 0; }
  .msheet, .msheet.wide { border-radius: 18px 18px 0 0; max-height: 94vh; padding-bottom: env(safe-area-inset-bottom, 0px); }
}
</style>
