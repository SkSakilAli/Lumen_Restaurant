<!-- Copyright (c) 2026 Lumen Solutions
     SPDX-License-Identifier: AGPL-3.0-only
     "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md. -->
<!-- The booking page designer. Every change is drawn at once in the preview
     beside it: the preview is the real public page, opened in preview mode, fed
     the unsaved draft over postMessage, so what the owner sees here is exactly
     what a customer will see after Save. -->
<template>
  <div class="bd">
    <div class="bd-top card">
      <div class="bd-title"><Icon name="image" /> {{ t('Booking page') }}</div>
      <select v-if="outlets.length > 1" v-model="outlet" class="bd-outlet" @change="load">
        <option v-for="o in outlets" :key="o" :value="o">{{ o }}</option>
      </select>
      <label class="bd-publish" :class="{ on: draft.published }">
        <input type="checkbox" v-model="draft.published" :true-value="1" :false-value="0" />
        {{ draft.published ? t('Published') : t('Hidden') }}
      </label>
      <div class="bd-link" dir="ltr">
        <span>{{ publicUrl }}</span>
        <button class="btn-ghost" :title="t('Copy the link')" @click="copyLink"><Icon name="check" /></button>
      </div>
      <button class="btn btn-outline" @click="openPage">{{ t('Open the page') }}</button>
      <button class="btn btn-primary" :disabled="saving || !dirty" @click="save">
        {{ saving ? t('Saving…') : dirty ? t('Save the design') : t('Saved') }}
      </button>
    </div>

    <div v-if="loading" class="bd-empty muted">{{ t('Loading…') }}</div>
    <div v-else class="bd-body">
      <!-- ============================== editor ============================== -->
      <aside class="bd-editor card">
        <nav class="bd-tabs">
          <button v-for="tab in tabs" :key="tab.key" :class="{ active: section === tab.key }" @click="section = tab.key">
            {{ t(tab.label) }}
          </button>
        </nav>

        <div class="bd-pane">
          <!-- ---------- look ---------- -->
          <template v-if="section === 'look'">
            <div class="bd-label">{{ t('Ready-made styles') }}</div>
            <div class="themes">
              <button v-for="theme in THEMES" :key="theme.name" class="theme" @click="applyTheme(theme)">
                <span class="swatch" :style="swatch(theme)"><span :style="{ background: theme.primary_color }"></span></span>
                {{ t(theme.name) }}
              </button>
            </div>

            <div class="bd-label">{{ t('Colours') }}</div>
            <div class="colour-row">
              <label>
                <input type="color" v-model="draft.primary_color" />
                <span>{{ t('Main colour') }}<small>{{ t('Buttons and highlights') }}</small></span>
              </label>
              <label>
                <input type="color" v-model="draft.card_color" />
                <span>{{ t('Form background') }}<small>{{ t('The card the form sits on') }}</small></span>
              </label>
            </div>

            <div class="bd-label">{{ t('Page background') }}</div>
            <div class="seg">
              <button v-for="bg in ['Solid', 'Gradient', 'Image']" :key="bg" :class="{ on: draft.background_type === bg }" @click="draft.background_type = bg">
                {{ t(bgLabel(bg)) }}
              </button>
            </div>
            <div class="colour-row" v-if="draft.background_type !== 'Image'">
              <label>
                <input type="color" v-model="draft.background_color" />
                <span>{{ draft.background_type === 'Gradient' ? t('From') : t('Colour') }}</span>
              </label>
              <label v-if="draft.background_type === 'Gradient'">
                <input type="color" v-model="draft.background_color_2" />
                <span>{{ t('To') }}</span>
              </label>
            </div>
            <ImagePick v-else v-model="draft.background_image" :label="t('Background image')" />

            <div class="bd-label">{{ t('Font') }}</div>
            <div class="fonts">
              <button
                v-for="font in FONTS"
                :key="font"
                class="font"
                :class="{ on: draft.font === font }"
                :style="{ fontFamily: `'${font}'` }"
                @click="draft.font = font"
              >
                احجز طاولتك<small>{{ font }}</small>
              </button>
            </div>

            <div class="bd-label">{{ t('Corners') }}</div>
            <div class="seg">
              <button v-for="c in ['Rounded', 'Soft', 'Sharp']" :key="c" :class="{ on: draft.corner_style === c }" @click="draft.corner_style = c">
                {{ t(c === 'Rounded' ? 'Round' : c === 'Soft' ? 'Soft' : 'Square') }}
              </button>
            </div>
          </template>

          <!-- ---------- content ---------- -->
          <template v-else-if="section === 'content'">
            <div class="two">
              <label class="bd-field"><span>{{ t('Title (Arabic)') }}</span><input v-model="draft.title" /></label>
              <label class="bd-field"><span>{{ t('Title (English)') }}</span><input v-model="draft.title_en" dir="ltr" /></label>
            </div>
            <div class="two">
              <label class="bd-field"><span>{{ t('Welcome line (Arabic)') }}</span><textarea v-model="draft.subtitle" rows="2"></textarea></label>
              <label class="bd-field"><span>{{ t('Welcome line (English)') }}</span><textarea v-model="draft.subtitle_en" rows="2" dir="ltr"></textarea></label>
            </div>
            <ImagePick v-model="draft.logo" :label="t('Logo')" contain />
            <ImagePick v-model="draft.cover_image" :label="t('Cover image (top of the form)')" />
            <div class="two">
              <label class="bd-field"><span>{{ t('Terms above the button (Arabic)') }}</span><textarea v-model="draft.terms" rows="3" :placeholder="t('Example: the table is held for 15 minutes')"></textarea></label>
              <label class="bd-field"><span>{{ t('Terms (English)') }}</span><textarea v-model="draft.terms_en" rows="3" dir="ltr"></textarea></label>
            </div>
            <div class="two">
              <label class="bd-field"><span>{{ t('Message after booking (Arabic)') }}</span><textarea v-model="draft.success_message" rows="3" :placeholder="t('Empty = the standard message')"></textarea></label>
              <label class="bd-field"><span>{{ t('Message after booking (English)') }}</span><textarea v-model="draft.success_message_en" rows="3" dir="ltr"></textarea></label>
            </div>
          </template>

          <!-- ---------- rules ---------- -->
          <template v-else-if="section === 'rules'">
            <label class="switch-line">
              <input type="checkbox" class="setting-toggle" v-model="draft.auto_confirm" :true-value="1" :false-value="0" />
              <span>
                <b>{{ t('Confirm bookings automatically') }}</b>
                <small>{{ t('On: a booking is confirmed the moment it arrives while the time still has room. Off: staff confirm each one on the Bookings screen.') }}</small>
              </span>
            </label>
            <div class="two">
              <label class="bd-field"><span>{{ t('Bookings from') }}</span><input type="time" v-model="draft.open_time" /></label>
              <label class="bd-field"><span>{{ t('Bookings until') }}</span><input type="time" v-model="draft.close_time" /></label>
            </div>
            <div class="two">
              <label class="bd-field">
                <span>{{ t('A booking every') }}</span>
                <select v-model.number="draft.slot_minutes">
                  <option v-for="m in [15, 20, 30, 45, 60, 90, 120]" :key="m" :value="m">{{ t('{n} min', { n: m }) }}</option>
                </select>
              </label>
              <label class="bd-field"><span>{{ t('Days ahead') }}</span><input type="number" min="1" max="90" v-model.number="draft.days_ahead" /></label>
            </div>
            <div class="two">
              <label class="bd-field"><span>{{ t('Smallest party') }}</span><input type="number" min="1" v-model.number="draft.min_guests" /></label>
              <label class="bd-field"><span>{{ t('Largest party online') }}</span><input type="number" min="1" v-model.number="draft.max_guests" /></label>
            </div>
            <label class="bd-field">
              <span>{{ t('Most guests in one time slot') }}</span>
              <input type="number" min="0" v-model.number="draft.slot_capacity" />
              <small class="muted">{{ t('0 = no limit. A full time is greyed out for the next customer.') }}</small>
            </label>
            <div class="bd-label">{{ t('Closed days') }}</div>
            <div class="days">
              <button v-for="d in DAYS" :key="d.key" :class="{ off: draft[d.key] }" @click="draft[d.key] = draft[d.key] ? 0 : 1">
                {{ t(d.label) }}
              </button>
            </div>
          </template>

          <!-- ---------- fields ---------- -->
          <template v-else-if="section === 'fields'">
            <p class="muted small">{{ t('Name and mobile are always asked. Add any question you want below.') }}</p>
            <label class="switch-line">
              <input type="checkbox" class="setting-toggle" v-model="draft.show_note" :true-value="1" :false-value="0" />
              <span><b>{{ t('A free note box') }}</b></span>
            </label>
            <div v-if="draft.show_note" class="two">
              <label class="bd-field"><span>{{ t('Its label (Arabic)') }}</span><input v-model="draft.note_label" :placeholder="t('Note (optional)')" /></label>
              <label class="bd-field"><span>{{ t('Its label (English)') }}</span><input v-model="draft.note_label_en" dir="ltr" /></label>
            </div>

            <div v-for="(f, i) in draft.fields" :key="f.key || i" class="block">
              <div class="block-head">
                <b>{{ f.label || t('New question') }}</b>
                <span class="muted small">{{ t(typeLabel(f.fieldtype)) }}</span>
                <span class="grow"></span>
                <button class="btn-ghost" :disabled="i === 0" @click="move(draft.fields, i, -1)">▲</button>
                <button class="btn-ghost" :disabled="i === draft.fields.length - 1" @click="move(draft.fields, i, 1)">▼</button>
                <button class="btn-ghost danger" @click="draft.fields.splice(i, 1)"><Icon name="close" /></button>
              </div>
              <div class="two">
                <label class="bd-field"><span>{{ t('Question (Arabic)') }}</span><input v-model="f.label" /></label>
                <label class="bd-field"><span>{{ t('Question (English)') }}</span><input v-model="f.label_en" dir="ltr" /></label>
              </div>
              <div class="two">
                <label class="bd-field">
                  <span>{{ t('Answer type') }}</span>
                  <select v-model="f.fieldtype">
                    <option v-for="ft in FIELD_TYPES" :key="ft.value" :value="ft.value">{{ t(ft.label) }}</option>
                  </select>
                </label>
                <label class="bd-field check-cell">
                  <input type="checkbox" v-model="f.required" :true-value="1" :false-value="0" />
                  <span>{{ t('Required') }}</span>
                </label>
              </div>
              <label v-if="f.fieldtype === 'Select'" class="bd-field">
                <span>{{ t('Choices, one per line: Arabic | English') }}</span>
                <textarea v-model="f.options" rows="3" placeholder="عيد ميلاد | Birthday"></textarea>
              </label>
              <label v-else-if="f.fieldtype !== 'Check'" class="bd-field">
                <span>{{ t('Hint inside the box') }}</span><input v-model="f.placeholder" />
              </label>
            </div>

            <div class="bd-label">{{ t('Add a question') }}</div>
            <div class="quick">
              <button v-for="q in QUICK_FIELDS" :key="q.label" class="btn btn-outline" @click="addField(q)">+ {{ t(q.name) }}</button>
            </div>
          </template>

          <!-- ---------- packages ---------- -->
          <template v-else-if="section === 'packages'">
            <p class="muted small">
              {{ t('Things the customer can pick with the booking: a buffet, a set menu, a cake. The price comes from the outlet price list, so the page and the till always agree.') }}
            </p>
            <div v-for="(it, i) in draft.items" :key="it.item_code" class="block">
              <div class="block-head">
                <b>{{ it.title || draft.item_names?.[it.item_code] || it.item_code }}</b>
                <span class="pill">{{ priceOf(it) }}</span>
                <span class="grow"></span>
                <button class="btn-ghost" :disabled="i === 0" @click="move(draft.items, i, -1)">▲</button>
                <button class="btn-ghost" :disabled="i === draft.items.length - 1" @click="move(draft.items, i, 1)">▼</button>
                <button class="btn-ghost danger" @click="draft.items.splice(i, 1)"><Icon name="close" /></button>
              </div>
              <div class="two">
                <label class="bd-field"><span>{{ t('Name (Arabic)') }}</span><input v-model="it.title" :placeholder="draft.item_names?.[it.item_code]" /></label>
                <label class="bd-field"><span>{{ t('Name (English)') }}</span><input v-model="it.title_en" dir="ltr" /></label>
              </div>
              <div class="two">
                <label class="bd-field"><span>{{ t('Description (Arabic)') }}</span><textarea v-model="it.description" rows="2"></textarea></label>
                <label class="bd-field"><span>{{ t('Description (English)') }}</span><textarea v-model="it.description_en" rows="2" dir="ltr"></textarea></label>
              </div>
              <div class="two">
                <label class="bd-field">
                  <span>{{ t('How it is priced') }}</span>
                  <select v-model="it.pricing">
                    <option value="Per guest">{{ t('Per guest (like a buffet)') }}</option>
                    <option value="Per booking">{{ t('The customer picks how many') }}</option>
                  </select>
                </label>
                <label class="bd-field" v-if="it.pricing !== 'Per guest'">
                  <span>{{ t('Most per booking') }}</span><input type="number" min="1" v-model.number="it.max_qty" />
                </label>
              </div>
              <label class="bd-field check-cell">
                <input type="checkbox" v-model="it.required" :true-value="1" :false-value="0" />
                <span>{{ t('Always included (the customer cannot remove it)') }}</span>
              </label>
              <ImagePick v-model="it.image" :label="t('Picture (empty = the item picture)')" />
            </div>
            <div class="bd-label">{{ t('Add a package') }}</div>
            <div class="add-item">
              <LinkPicker doctype="Item" v-model="newItem" :placeholder="t('Search the items…')" />
              <button class="btn btn-primary" :disabled="!newItem" @click="addItem">{{ t('Add') }}</button>
            </div>
          </template>

          <!-- ---------- contact ---------- -->
          <template v-else-if="section === 'contact'">
            <p class="muted small">{{ t('Shown as buttons under the form. Leave empty what you do not use.') }}</p>
            <label class="bd-field"><span>{{ t('Phone') }}</span><input v-model="draft.contact_phone" dir="ltr" placeholder="0112345678" /></label>
            <label class="bd-field"><span>WhatsApp</span><input v-model="draft.whatsapp" dir="ltr" placeholder="0551234567" /></label>
            <label class="bd-field"><span>{{ t('Location link (Google Maps)') }}</span><input v-model="draft.maps_url" dir="ltr" placeholder="https://maps.app.goo.gl/..." /></label>
            <label class="bd-field"><span>{{ t('Website') }}</span><input v-model="draft.website" dir="ltr" placeholder="https://" /></label>
            <div class="two">
              <label class="bd-field"><span>Instagram</span><input v-model="draft.instagram" dir="ltr" placeholder="@restaurant" /></label>
              <label class="bd-field"><span>Snapchat</span><input v-model="draft.snapchat" dir="ltr" placeholder="@restaurant" /></label>
            </div>
            <div class="two">
              <label class="bd-field"><span>TikTok</span><input v-model="draft.tiktok" dir="ltr" placeholder="@restaurant" /></label>
              <label class="bd-field"><span>X</span><input v-model="draft.x_url" dir="ltr" placeholder="@restaurant" /></label>
            </div>
            <template v-if="outlets.length > 1">
              <div class="bd-label">{{ t('Use the same design at another branch') }}</div>
              <div class="add-item">
                <select v-model="copyFrom">
                  <option :value="null">{{ t('Copy the design from…') }}</option>
                  <option v-for="o in outlets.filter((x) => x !== outlet)" :key="o" :value="o">{{ o }}</option>
                </select>
                <button class="btn btn-outline" :disabled="!copyFrom" @click="copyDesign">{{ t('Copy') }}</button>
              </div>
            </template>
          </template>
        </div>
      </aside>

      <!-- ============================== preview ============================== -->
      <main class="bd-preview card">
        <div class="pv-bar">
          <div class="seg small">
            <button :class="{ on: device === 'phone' }" @click="device = 'phone'">{{ t('On a phone') }}</button>
            <button :class="{ on: device === 'desktop' }" @click="device = 'desktop'">{{ t('On a computer') }}</button>
          </div>
          <div class="seg small">
            <button :class="{ on: previewLang === 'ar' }" @click="previewLang = 'ar'">العربية</button>
            <button :class="{ on: previewLang === 'en' }" @click="previewLang = 'en'">English</button>
          </div>
          <span class="muted small">{{ t('Live preview: what customers will see after you save') }}</span>
        </div>
        <div class="pv-stage">
          <iframe
            ref="frame"
            :class="device"
            :src="previewSrc"
            title="preview"
            @load="pushPreview"
          ></iframe>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, defineComponent, h } from 'vue'
import Icon from '../components/Icon.vue'
import LinkPicker from '../components/LinkPicker.vue'
import { call } from '../api'
import { useSessionStore } from '../stores/session'
import { money } from '../format'
import { t } from '../i18n'

const session = useSessionStore()

const FONTS = [
  'IBM Plex Sans Arabic', 'Tajawal', 'Cairo', 'Almarai', 'Noto Kufi Arabic', 'Readex Pro',
  'El Messiri', 'Changa', 'Reem Kufi', 'Amiri', 'Noto Naskh Arabic', 'Lalezar',
]
const THEMES = [
  { name: 'Classic', primary_color: '#1463ff', card_color: '#ffffff', background_type: 'Solid', background_color: '#f3f5f9', background_color_2: '#dfe7f5', font: 'IBM Plex Sans Arabic', corner_style: 'Rounded' },
  { name: 'Night', primary_color: '#d4a64a', card_color: '#151a24', background_type: 'Gradient', background_color: '#0b0f17', background_color_2: '#1d2433', font: 'Readex Pro', corner_style: 'Rounded' },
  { name: 'Gold', primary_color: '#a8781f', card_color: '#fffaf0', background_type: 'Gradient', background_color: '#fdf6e3', background_color_2: '#efdcb4', font: 'El Messiri', corner_style: 'Soft' },
  { name: 'Olive', primary_color: '#55702f', card_color: '#ffffff', background_type: 'Solid', background_color: '#eef1e6', background_color_2: '#dfe6cf', font: 'Tajawal', corner_style: 'Rounded' },
  { name: 'Coffee', primary_color: '#6f4e37', card_color: '#fffdf9', background_type: 'Gradient', background_color: '#f4ece4', background_color_2: '#e3d2c2', font: 'Almarai', corner_style: 'Soft' },
  { name: 'Rose', primary_color: '#c2185b', card_color: '#ffffff', background_type: 'Gradient', background_color: '#fde4ec', background_color_2: '#f3ecff', font: 'Cairo', corner_style: 'Rounded' },
  { name: 'Sea', primary_color: '#00838f', card_color: '#ffffff', background_type: 'Gradient', background_color: '#e0f7fa', background_color_2: '#e8eaf6', font: 'Noto Kufi Arabic', corner_style: 'Rounded' },
  { name: 'Mono', primary_color: '#111111', card_color: '#ffffff', background_type: 'Solid', background_color: '#e9e9e9', background_color_2: '#d6d6d6', font: 'Changa', corner_style: 'Sharp' },
]
const DAYS = [
  { key: 'closed_sat', label: 'Sat' }, { key: 'closed_sun', label: 'Sun' }, { key: 'closed_mon', label: 'Mon' },
  { key: 'closed_tue', label: 'Tue' }, { key: 'closed_wed', label: 'Wed' }, { key: 'closed_thu', label: 'Thu' },
  { key: 'closed_fri', label: 'Fri' },
]
const FIELD_TYPES = [
  { value: 'Text', label: 'Short text' }, { value: 'Long Text', label: 'Long text' },
  { value: 'Number', label: 'Number' }, { value: 'Select', label: 'A list to pick from' },
  { value: 'Check', label: 'Yes / no tick' }, { value: 'Date', label: 'Date' },
]
const QUICK_FIELDS = [
  { name: 'Occasion', label: 'المناسبة', label_en: 'Occasion', fieldtype: 'Select',
    options: 'عيد ميلاد | Birthday\nذكرى زواج | Anniversary\nاجتماع عمل | Business\nأخرى | Other' },
  { name: 'Seating', label: 'مكان الجلوس', label_en: 'Seating', fieldtype: 'Select',
    options: 'داخلي | Indoor\nخارجي | Outdoor\nعائلي | Family' },
  { name: 'High chair', label: 'نحتاج كرسي أطفال', label_en: 'We need a high chair', fieldtype: 'Check' },
  { name: 'Email', label: 'البريد الإلكتروني', label_en: 'Email', fieldtype: 'Text', placeholder: 'name@example.com' },
  { name: 'Empty question', label: '', label_en: '', fieldtype: 'Text' },
]
const tabs = [
  { key: 'look', label: 'Look' }, { key: 'content', label: 'Content' }, { key: 'rules', label: 'Booking' },
  { key: 'fields', label: 'Questions' }, { key: 'packages', label: 'Packages' }, { key: 'contact', label: 'Contact' },
]

// One image field: upload to the site's public files, or clear.
const ImagePick = defineComponent({
  props: { modelValue: String, label: String, contain: Boolean },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const busy = ref(false)
    const input = ref(null)
    async function upload(event) {
      const file = event.target.files?.[0]
      if (!file) return
      busy.value = true
      try {
        const form = new FormData()
        form.append('file', file, file.name)
        form.append('is_private', '0')
        form.append('folder', 'Home')
        const res = await fetch('/api/method/upload_file', {
          method: 'POST',
          headers: { 'X-Frappe-CSRF-Token': window.csrf_token || '', Accept: 'application/json' },
          body: form,
        })
        const data = await res.json()
        if (!res.ok || !data.message?.file_url) throw new Error(t('The picture could not be uploaded'))
        emit('update:modelValue', data.message.file_url)
      } catch (e) {
        session.notify(e.message, true)
      } finally {
        busy.value = false
        event.target.value = ''
      }
    }
    return () =>
      h('div', { class: 'imgpick' }, [
        h('span', { class: 'imgpick-label' }, props.label),
        h('div', { class: 'imgpick-row' }, [
          props.modelValue
            ? h('img', { src: props.modelValue, class: props.contain ? 'contain' : '' })
            : h('div', { class: 'imgpick-empty' }, t('No picture')),
          h('input', { type: 'file', accept: 'image/*', ref: input, style: 'display:none', onChange: upload }),
          h('button', { class: 'btn btn-outline', disabled: busy.value, onClick: () => input.value?.click() },
            busy.value ? t('Uploading…') : props.modelValue ? t('Change picture') : t('Upload')),
          props.modelValue
            ? h('button', { class: 'btn-ghost danger', onClick: () => emit('update:modelValue', null) }, t('Remove'))
            : null,
        ]),
      ])
  },
})

const outlets = computed(() => session.availableProfiles?.length ? session.availableProfiles : [session.posProfile])
const outlet = ref(session.posProfile)
const draft = ref({ fields: [], items: [] })
const saved = ref('')
const loading = ref(true)
const saving = ref(false)
const section = ref('look')
const device = ref('phone')
const previewLang = ref('ar')
const newItem = ref('')
const copyFrom = ref(null)
const frame = ref(null)

const dirty = computed(() => JSON.stringify(strip(draft.value)) !== saved.value)
const publicUrl = computed(() => location.origin + '/book/' + encodeURIComponent(outlet.value || ''))
const previewSrc = computed(() => '/book/' + encodeURIComponent(outlet.value || '') + '?preview=1')

function strip(page) {
  const copy = { ...page }
  delete copy.rates
  delete copy.item_names
  delete copy.item_images
  delete copy.exists
  return copy
}

function bgLabel(bg) {
  return bg === 'Solid' ? 'One colour' : bg === 'Gradient' ? 'Two colours' : 'A picture'
}
function typeLabel(ft) {
  return FIELD_TYPES.find((x) => x.value === ft)?.label || ft
}
function swatch(theme) {
  const bg = theme.background_type === 'Gradient'
    ? `linear-gradient(160deg, ${theme.background_color}, ${theme.background_color_2})`
    : theme.background_color
  return { background: bg }
}
function applyTheme(theme) {
  for (const key of ['primary_color', 'card_color', 'background_type', 'background_color', 'background_color_2', 'font', 'corner_style']) {
    draft.value[key] = theme[key]
  }
}
function move(list, i, step) {
  const [row] = list.splice(i, 1)
  list.splice(i + step, 0, row)
}
function addField(q) {
  draft.value.fields.push({
    key: Math.random().toString(36).slice(2, 10),
    label: q.label, label_en: q.label_en, fieldtype: q.fieldtype,
    options: q.options || '', required: 0, placeholder: q.placeholder || '',
  })
}
function priceOf(it) {
  const rate = draft.value.rates?.[it.item_code]
  if (!rate) return t('No price on the price list')
  return money(rate) + (it.pricing === 'Per guest' ? ' ' + t('per guest') : '')
}

async function addItem() {
  const code = newItem.value
  if (!code) return
  if (draft.value.items.some((x) => x.item_code === code)) {
    newItem.value = ''
    return session.notify(t('That item is already on the page'), true)
  }
  try {
    const info = await call('lumen_restaurants.api.booking_page.item_info', { pos_profile: outlet.value, item_code: code })
    draft.value.rates = { ...(draft.value.rates || {}), [code]: info.rate }
    draft.value.item_names = { ...(draft.value.item_names || {}), [code]: info.item_name }
    draft.value.item_images = { ...(draft.value.item_images || {}), [code]: info.image }
    draft.value.items.push({
      item_code: code, title: info.item_name, title_en: '', description: '', description_en: '',
      image: null, pricing: 'Per booking', required: 0, max_qty: 10,
    })
    newItem.value = ''
  } catch (e) {
    session.notify(e.message, true)
  }
}

async function load() {
  loading.value = true
  try {
    const page = await call('lumen_restaurants.api.booking_page.get_page', { pos_profile: outlet.value })
    for (const key of ['open_time', 'close_time']) if (page[key]) page[key] = String(page[key]).slice(0, 5)
    page.fields = page.fields || []
    page.items = page.items || []
    draft.value = page
    saved.value = JSON.stringify(strip(page))
  } catch (e) {
    session.notify(e.message, true)
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    const page = await call('lumen_restaurants.api.booking_page.save_page', { pos_profile: outlet.value, page: strip(draft.value) })
    for (const key of ['open_time', 'close_time']) if (page[key]) page[key] = String(page[key]).slice(0, 5)
    draft.value = page
    saved.value = JSON.stringify(strip(page))
    session.notify(page.published ? t('Saved. The page is live.') : t('Saved. The page is hidden until you publish it.'))
  } catch (e) {
    session.notify(e.message, true)
  } finally {
    saving.value = false
  }
}

async function copyDesign() {
  if (!copyFrom.value) return
  if (!confirm(t('Replace this design with the one from {o}?', { o: copyFrom.value }))) return
  try {
    const page = await call('lumen_restaurants.api.booking_page.copy_design', { source: copyFrom.value, target: outlet.value })
    for (const key of ['open_time', 'close_time']) if (page[key]) page[key] = String(page[key]).slice(0, 5)
    draft.value = page
    saved.value = JSON.stringify(strip(page))
    copyFrom.value = null
    session.notify(t('Design copied'))
  } catch (e) {
    session.notify(e.message, true)
  }
}

function copyLink() {
  navigator.clipboard.writeText(publicUrl.value).then(
    () => session.notify(t('Link copied: {url}', { url: publicUrl.value })),
    () => session.notify(publicUrl.value)
  )
}
function openPage() {
  window.open(dirty.value || !draft.value.published ? previewSrc.value : publicUrl.value, '_blank')
}

// The preview is the real page in preview mode, fed the draft on every change.
let pushTimer = null
function pushPreview() {
  clearTimeout(pushTimer)
  pushTimer = setTimeout(() => {
    const win = frame.value?.contentWindow
    if (!win) return
    win.postMessage(
      { type: 'lumenpos-booking-preview', page: JSON.parse(JSON.stringify(draft.value)), lang: previewLang.value },
      location.origin
    )
  }, 120)
}
watch(draft, pushPreview, { deep: true })
watch(previewLang, pushPreview)

// The font picker has to show each font in itself, so the designer loads the
// whole list once (the till proper only ever loads its own two faces).
function loadFonts() {
  if (document.getElementById('bd-fonts')) return
  const families = FONTS.map((f) => 'family=' + f.replace(/ /g, '+') + (f === 'Lalezar' ? '' : ':wght@400;700'))
  const link = document.createElement('link')
  link.id = 'bd-fonts'
  link.rel = 'stylesheet'
  link.href = 'https://fonts.googleapis.com/css2?' + families.join('&') + '&display=swap'
  document.head.appendChild(link)
}

onMounted(() => {
  loadFonts()
  load()
})
</script>

<style scoped>
.bd { flex: 1; display: flex; flex-direction: column; gap: 12px; padding: 14px; overflow: hidden; }
.bd-top { display: flex; align-items: center; gap: 10px; padding: 10px 14px; flex-wrap: wrap; }
.bd-title { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 15px; margin-inline-end: auto; }
.bd-outlet { padding: 7px 10px; border: 1px solid var(--border); border-radius: 9px; font: inherit; font-size: 13px; }
.bd-publish {
  display: inline-flex; align-items: center; gap: 7px; border: 1.5px solid var(--border); border-radius: 999px;
  padding: 6px 14px; font-size: 13px; font-weight: 700; cursor: pointer; color: var(--text-muted);
}
.bd-publish.on { border-color: var(--brand); color: var(--brand-dark); background: rgba(20, 99, 255, 0.08); }
.bd-link { display: inline-flex; align-items: center; gap: 4px; background: var(--surface-2); border-radius: 9px; padding: 3px 4px 3px 12px; font-size: 12px; max-width: 320px; }
.bd-link span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.bd-empty { padding: 40px; text-align: center; }
.bd-body { flex: 1; min-height: 0; display: flex; gap: 12px; }
.bd-editor { width: 440px; flex: none; display: flex; flex-direction: column; overflow: hidden; }
.bd-tabs { display: flex; gap: 4px; padding: 10px 10px 0; flex-wrap: wrap; border-bottom: 1px solid var(--border); }
.bd-tabs button {
  border: 0; background: transparent; font: inherit; font-size: 13px; font-weight: 600; color: var(--text-muted);
  padding: 8px 12px; border-bottom: 2.5px solid transparent; cursor: pointer;
}
.bd-tabs button.active { color: var(--brand); border-bottom-color: var(--brand); }
.bd-pane { flex: 1; overflow: auto; padding: 14px 16px 24px; }
.bd-label { font-size: 12.25px; font-weight: 700; color: var(--text-muted); margin: 18px 0 8px; }
.bd-label:first-child { margin-top: 0; }
.themes { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
.theme { border: 1px solid var(--border); background: var(--card-bg); border-radius: 12px; padding: 7px; font: inherit; font-size: 12px; font-weight: 600; cursor: pointer; color: var(--text); display: flex; flex-direction: column; gap: 5px; }
.swatch { height: 38px; border-radius: 8px; display: flex; align-items: flex-end; justify-content: center; padding-bottom: 5px; }
.swatch span { width: 44%; height: 9px; border-radius: 99px; }
.colour-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.colour-row label { display: flex; align-items: center; gap: 10px; border: 1px solid var(--border); border-radius: 11px; padding: 8px; cursor: pointer; }
.colour-row input[type='color'] { width: 38px; height: 38px; border: 0; padding: 0; background: none; cursor: pointer; flex: none; }
.colour-row span { font-size: 13px; font-weight: 600; display: flex; flex-direction: column; }
.colour-row small { font-weight: 400; color: var(--text-muted); font-size: 11.5px; }
.seg { display: inline-flex; background: var(--surface-2); border-radius: 11px; padding: 3px; gap: 3px; margin-bottom: 10px; }
.seg button { border: 0; background: transparent; border-radius: 9px; padding: 7px 14px; font: inherit; font-size: 12.5px; font-weight: 600; color: var(--text-muted); cursor: pointer; }
.seg button.on { background: var(--card-bg); color: var(--text); box-shadow: var(--shadow); }
.seg.small { margin: 0; }
.seg.small button { padding: 5px 11px; }
.fonts { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
.font { border: 1.5px solid var(--border); background: var(--card-bg); border-radius: 11px; padding: 9px 10px; font-size: 17px; cursor: pointer; color: var(--text); text-align: start; display: flex; flex-direction: column; gap: 2px; }
.font small { font-family: var(--font); font-size: 11px; color: var(--text-muted); }
.font.on { border-color: var(--brand); box-shadow: 0 0 0 1px var(--brand) inset; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.bd-field { display: flex; flex-direction: column; gap: 5px; margin-bottom: 12px; }
.bd-field > span { font-size: 12.25px; font-weight: 600; color: var(--text-muted); }
.bd-field input, .bd-field select, .bd-field textarea { width: 100%; box-sizing: border-box; padding: 8px 10px; font: inherit; font-size: 13.5px; border-radius: 9px; }
.check-cell { flex-direction: row; align-items: center; gap: 8px; align-self: end; }
.check-cell input { width: 18px; height: 18px; }
.switch-line { display: flex; gap: 10px; align-items: flex-start; margin-bottom: 14px; cursor: pointer; }
.switch-line span { display: flex; flex-direction: column; gap: 2px; font-size: 13.5px; }
.switch-line small { color: var(--text-muted); font-size: 12.25px; line-height: 1.5; }
.days { display: flex; gap: 6px; flex-wrap: wrap; }
.days button { border: 1.5px solid var(--border); background: var(--card-bg); border-radius: 10px; padding: 8px 12px; font: inherit; font-size: 12.5px; font-weight: 600; cursor: pointer; color: var(--text); }
.days button.off { background: rgba(214, 69, 69, 0.1); border-color: rgba(214, 69, 69, 0.5); color: var(--red); text-decoration: line-through; }
.block { border: 1px solid var(--border); border-radius: 13px; padding: 10px 12px 2px; margin: 12px 0; background: var(--card-bg); }
.block-head { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.block-head b { font-size: 13.5px; }
.grow { flex: 1; }
.pill { background: var(--surface-2); border-radius: 8px; padding: 2px 9px; font-size: 11.5px; white-space: nowrap; }
.danger { color: var(--red); }
.quick { display: flex; gap: 7px; flex-wrap: wrap; }
.quick .btn { padding: 7px 12px; font-size: 12.5px; }
.add-item { display: flex; gap: 8px; align-items: center; }
.add-item > :first-child { flex: 1; }
.add-item select { padding: 8px 10px; border: 1px solid var(--border); border-radius: 9px; font: inherit; }
:deep(.imgpick) { margin-bottom: 12px; }
:deep(.imgpick-label) { display: block; font-size: 12.25px; font-weight: 600; color: var(--text-muted); margin-bottom: 6px; }
:deep(.imgpick-row) { display: flex; align-items: center; gap: 8px; }
:deep(.imgpick-row img) { width: 64px; height: 64px; object-fit: cover; border-radius: 10px; border: 1px solid var(--border); background: var(--surface-2); }
:deep(.imgpick-row img.contain) { object-fit: contain; }
:deep(.imgpick-empty) { width: 64px; height: 64px; border-radius: 10px; border: 1.5px dashed var(--border); display: grid; place-items: center; font-size: 10.5px; color: var(--text-muted); text-align: center; }
.bd-preview { flex: 1; min-width: 0; display: flex; flex-direction: column; overflow: hidden; }
.pv-bar { display: flex; align-items: center; gap: 10px; padding: 10px 14px; border-bottom: 1px solid var(--border); flex-wrap: wrap; }
.pv-stage { flex: 1; overflow: auto; background: var(--page-bg); display: flex; justify-content: center; padding: 14px; }
.pv-stage iframe { border: 0; background: #fff; box-shadow: var(--shadow-md); }
.pv-stage iframe.phone { width: 390px; height: 100%; min-height: 640px; border-radius: 26px; border: 10px solid #11151e; }
.pv-stage iframe.desktop { width: 100%; height: 100%; min-height: 640px; border-radius: 12px; }
@media (max-width: 1000px) {
  .bd { overflow: auto; }
  .bd-body { flex-direction: column; }
  .bd-editor { width: 100%; }
  .pv-stage iframe.phone { width: 100%; max-width: 390px; }
}
</style>
