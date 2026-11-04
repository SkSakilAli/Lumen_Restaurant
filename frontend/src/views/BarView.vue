<!-- Copyright (c) 2026 Lumen Solutions
     SPDX-License-Identifier: AGPL-3.0-only
     "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md. -->
<template>
  <div class="kds bar-kds">
    <div class="card kds-card">
      <!-- Bar Header with Tab Navigation -->
      <div class="kds-head">
        <div class="kds-title">
          <Icon name="glass" />
          <span>{{ t('Bar') }}</span>
        </div>

        <!-- Mode Navigation Tabs -->
        <div class="bar-nav-tabs">
          <button
            class="bar-tab-btn"
            :class="{ active: currentTab === 'tickets' }"
            @click="currentTab = 'tickets'"
          >
            <span>{{ t('Live Tickets') }}</span>
            <span v-if="tickets.length" class="tab-badge">{{ tickets.length }}</span>
          </button>
          <button
            class="bar-tab-btn"
            :class="{ active: currentTab === 'taps' }"
            @click="switchTab('taps')"
          >
            <span>{{ t('Taps & Kegs') }}</span>
            <span v-if="lowTapsCount" class="tab-badge warn">{{ lowTapsCount }}</span>
          </button>
          <button
            class="bar-tab-btn"
            :class="{ active: currentTab === 'recipes' }"
            @click="switchTab('recipes')"
          >
            <span>{{ t('Recipes (BOM)') }}</span>
          </button>
          <button
            class="bar-tab-btn"
            :class="{ active: currentTab === 'spillage' }"
            @click="switchTab('spillage')"
          >
            <span>{{ t('Spillage & Waste') }}</span>
          </button>
        </div>

        <span v-if="currentTab === 'tickets' && avgText" class="kpill">{{ t('Average today: {t}', { t: avgText }) }}</span>
        <button
          v-if="currentTab === 'spillage'"
          class="btn btn-primary bar-action-btn"
          @click="openSpillModal"
        >
          <Icon name="plus" /> {{ t('Log Spillage') }}
        </button>
        <button class="btn btn-outline" :title="t('Refresh')" @click="refreshCurrent">
          <Icon name="refresh" />
        </button>
      </div>

      <div v-if="session.offline" class="kempty muted">{{ t('The bar screen needs a connection.') }}</div>
      <div v-else-if="loading" class="kempty muted">{{ t('Loading…') }}</div>

      <!-- TAB 1: LIVE ORDERS (KDS) -->
      <div v-else-if="currentTab === 'tickets'" class="kcols">
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
              <li v-for="(row, i) in ticket.items" :key="i" class="kitem-row">
                <div class="kitem-main" @click="inspectDrink(row.item_code, row.item_name)">
                  <b>×{{ row.qty }}</b>
                  <span class="drink-name">{{ row.item_name }}</span>
                  <span class="recipe-hint" :title="t('View Recipe Specs')"><Icon name="bulb" :size="13" /></span>
                </div>
                <span v-if="row.note" class="knote">{{ row.note }}</span>
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
              <button class="kbtn print" :title="t('Print the bar slip')" @click="printSlip(ticket)">
                <Icon name="report" />
              </button>
            </div>
            <div v-if="ticket.status === 'Ready'" class="kready-note">
              {{ ticket.order_no ? t('Call number {n}', { n: ticket.order_no }) : t('Take it to {t}', { t: ticket.table_label }) }}
            </div>
          </div>
        </div>
      </div>

      <!-- TAB 2: TAPS & KEGS MANAGEMENT -->
      <div v-else-if="currentTab === 'taps'" class="bar-panel-view">
        <div class="bar-panel-subhead">
          <div class="panel-desc">
            <h3>{{ t('Draft Beer & Dispenser Lines') }}</h3>
            <p class="muted small">{{ t('Track keg remaining volumes, change kegs, and manage line maintenance.') }}</p>
          </div>
          <button class="btn btn-outline" @click="openTapModal(null)">
            <Icon name="plus" /> {{ t('Add Tap Line') }}
          </button>
        </div>

        <div class="taps-grid">
          <div
            v-for="tap in taps"
            :key="tap.name"
            class="tap-card"
            :class="{ kicking: tap.status === 'Kicking Soon', empty: tap.status === 'Empty' }"
          >
            <div class="tap-head">
              <span class="tap-no">{{ tap.tap_number }}</span>
              <span class="tap-station muted">{{ tap.station }}</span>
              <span class="tap-badge" :class="tap.status.toLowerCase().replace(/[\s\/]+/g, '-')">
                {{ tap.status }}
              </span>
            </div>

            <div class="tap-body">
              <div class="tap-beer-name">{{ tap.item_name || tap.keg_item || t('No Keg Connected') }}</div>
              <div class="tap-vol-row">
                <span class="tap-rem"><b>{{ formatVol(tap.remaining_liters) }}</b> / {{ formatVol(tap.capacity_liters) }} {{ tap.unit || 'ml' }}</span>
                <span class="tap-pct" :class="{ warn: tap.percent <= 15 }">{{ tap.percent }}%</span>
              </div>
              <div class="tap-gauge">
                <div
                  class="tap-gauge-fill"
                  :style="{ width: tap.percent + '%' }"
                  :class="{ warn: tap.percent <= 20, critical: tap.percent <= 10 }"
                />
              </div>
            </div>

            <div class="tap-actions">
              <button class="btn btn-sm btn-outline tap-btn" @click="openTapModal(tap, 'tap_new_keg')">
                <Icon name="refresh" :size="14" /> {{ t('Tap New Keg') }}
              </button>
              <button class="btn btn-sm btn-ghost tap-btn" @click="openTapModal(tap, 'edit')">
                {{ t('Edit') }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- TAB 3: RECIPES (BEVERAGE BOM & POUR SPECS) -->
      <div v-else-if="currentTab === 'recipes'" class="bar-panel-view">
        <div class="bar-panel-subhead">
          <div class="panel-desc">
            <h3>{{ t('Drink Recipes & Pour Standards') }}</h3>
            <p class="muted small">{{ t('Cocktail formulations, glass specifications, and ingredient milliliter breakdowns.') }}</p>
          </div>
          <div class="recipe-filters">
            <input
              v-model="recipeSearch"
              class="input bar-search"
              :placeholder="t('Search drinks or spirits…')"
            />
            <select v-model="recipeCategory" class="input bar-cat-select" @change="loadRecipes">
              <option value="All">{{ t('All Categories') }}</option>
              <option value="Cocktail">{{ t('Cocktails') }}</option>
              <option value="Spirits & Shots">{{ t('Spirits & Shots') }}</option>
              <option value="Draft Beer">{{ t('Draft Beer') }}</option>
              <option value="Wine by the Glass">{{ t('Wine by the Glass') }}</option>
              <option value="Mocktail / Non-Alcoholic">{{ t('Mocktails') }}</option>
            </select>
            <button class="btn btn-outline" @click="openRecipeModal(null)">
              <Icon name="plus" /> {{ t('New Recipe') }}
            </button>
          </div>
        </div>

        <div v-if="!recipes.length" class="kempty muted">{{ t('No drink recipes found. Click "New Recipe" to add one.') }}</div>
        <div v-else class="recipes-grid">
          <div
            v-for="rec in filteredRecipes"
            :key="rec.name"
            class="recipe-card"
            @click="inspectRecipe(rec)"
          >
            <div class="rec-top">
              <span class="rec-glass-icon"><Icon name="glass" :size="18" /></span>
              <div class="rec-info">
                <div class="rec-name">{{ rec.recipe_name }}</div>
                <div class="rec-meta muted small">{{ rec.category }} • {{ rec.glassware }}</div>
              </div>
              <button
                class="btn btn-sm btn-ghost rec-edit-btn"
                :title="t('Edit Recipe')"
                @click.stop="openRecipeModal(rec)"
              >
                <Icon name="tag" :size="13" /> {{ t('Edit') }}
              </button>
            </div>

            <div class="rec-ingredients">
              <div
                v-for="(ing, idx) in (rec.ingredients || []).slice(0, 4)"
                :key="idx"
                class="rec-ing-row"
              >
                <span class="ing-name">{{ ing.ingredient_name }}</span>
                <span class="ing-qty"><b>{{ ing.pour_qty }}</b> {{ ing.pour_uom }}</span>
              </div>
              <div v-if="(rec.ingredients || []).length > 4" class="rec-more muted small">
                + {{ rec.ingredients.length - 4 }} {{ t('more ingredients') }}
              </div>
            </div>

            <div v-if="rec.prep_instructions" class="rec-prep-preview muted small">
              {{ rec.prep_instructions }}
            </div>
          </div>
        </div>
      </div>

      <!-- TAB 4: SPILLAGE & WASTAGE -->
      <div v-else-if="currentTab === 'spillage'" class="bar-panel-view">
        <div class="bar-panel-subhead">
          <div class="panel-desc">
            <h3>{{ t('Bar Spillage & Shrinkage Log') }}</h3>
            <p class="muted small">{{ t('Audit records for broken bottles, foam line flush, and drink remakes.') }}</p>
          </div>
          <div class="spill-summary-pill">
            <span>{{ t("Today's Wastage:") }}</span>
            <b>{{ formatCurrency(todaySpillTotal) }}</b>
          </div>
        </div>

        <div v-if="!spillages.length" class="kempty muted">{{ t('No spillage logged yet.') }}</div>
        <div v-else class="spill-table-wrap">
          <table class="bar-table">
            <thead>
              <tr>
                <th>{{ t('Timestamp') }}</th>
                <th>{{ t('Reason') }}</th>
                <th>{{ t('Items Wasted') }}</th>
                <th>{{ t('Cost') }}</th>
                <th>{{ t('Logged By') }}</th>
                <th>{{ t('Notes') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="sp in spillages" :key="sp.name">
                <td>{{ formatTimestamp(sp.creation) }}</td>
                <td><span class="spill-reason-tag">{{ sp.reason }}</span></td>
                <td>
                  <div v-for="it in sp.items || []" :key="it.item_code" class="spill-item-entry">
                    <b>{{ it.qty }} {{ it.uom || 'Nos' }}</b> — {{ it.item_name }}
                  </div>
                </td>
                <td class="font-bold">{{ formatCurrency(sp.total_cost) }}</td>
                <td class="muted">{{ sp.bartender }}</td>
                <td class="muted small">{{ sp.notes || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- MODAL: RECIPE SPECS INSPECTOR -->
    <div v-if="inspectedRecipe" class="bar-modal-backdrop" @click.self="inspectedRecipe = null">
      <div class="bar-modal card">
        <div class="modal-head">
          <div class="modal-title">
            <Icon name="glass" />
            <span>{{ inspectedRecipe.recipe_name }}</span>
          </div>
          <button class="btn btn-ghost" @click="inspectedRecipe = null"><Icon name="close" /></button>
        </div>
        <div class="modal-body">
          <div class="recipe-modal-badges">
            <span class="pill-badge">{{ inspectedRecipe.category }}</span>
            <span class="pill-badge outline">{{ t('Glass: {g}', { g: inspectedRecipe.glassware }) }}</span>
            <span v-if="inspectedRecipe.serving_size_ml" class="pill-badge outline">
              {{ inspectedRecipe.serving_size_ml }} ml
            </span>
          </div>

          <h4 class="section-title">{{ t('Ingredients & Pour Ratios') }}</h4>
          <ul class="spec-ing-list">
            <li v-for="(ing, idx) in (inspectedRecipe.ingredients || [])" :key="idx">
              <span class="spec-ing-name">
                {{ ing.ingredient_name }}
                <b v-if="ing.is_primary_spirit" class="primary-tag">{{ t('Base Spirit') }}</b>
              </span>
              <span class="spec-ing-pour"><b>{{ ing.pour_qty }}</b> {{ ing.pour_uom }}</span>
            </li>
          </ul>

          <div v-if="inspectedRecipe.prep_instructions" class="spec-prep-box">
            <h4 class="section-title">{{ t('Bartender Instructions & Garnish') }}</h4>
            <p>{{ inspectedRecipe.prep_instructions }}</p>
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn btn-outline" @click="inspectedRecipe = null">{{ t('Close') }}</button>
          <button class="btn btn-primary" @click="editInspectedRecipe">
            <Icon name="tag" :size="13" /> {{ t('Edit Recipe') }}
          </button>
        </div>
      </div>
    </div>

    <!-- MODAL: RECIPE EDITOR (CREATE / EDIT) -->
    <div v-if="recipeModalOpen" class="bar-modal-backdrop" @click.self="recipeModalOpen = false">
      <div class="bar-modal card recipe-editor-modal">
        <div class="modal-head">
          <div class="modal-title">
            <Icon name="glass" />
            <span>{{ recipeForm.name ? t('Edit Recipe: {n}', { n: recipeForm.recipe_name }) : t('New Drink Recipe (BOM)') }}</span>
          </div>
          <button class="btn btn-ghost" @click="recipeModalOpen = false"><Icon name="close" /></button>
        </div>
        <div class="modal-body form-grid">
          <div class="form-row">
            <label>{{ t('Link to Menu Item (Item Master)') }}</label>
            <select v-model="selectedMenuItem" class="input" @change="onSelectMenuItem">
              <option value="">-- {{ t('Select an Item or type custom name') }} --</option>
              <option v-for="it in menuItems" :key="it.item_code" :value="it.item_code">
                {{ it.item_name }} ({{ it.item_group }})
              </option>
            </select>
          </div>

          <div class="form-row-group">
            <div class="form-row">
              <label>{{ t('Drink / Recipe Name') }} *</label>
              <input v-model="recipeForm.recipe_name" class="input" placeholder="e.g. 30 ML Wine" />
            </div>
            <div class="form-row">
              <label>{{ t('ERPNext Item Code') }}</label>
              <input v-model="recipeForm.item_code" class="input" placeholder="Leave blank to match name" />
            </div>
          </div>

          <div class="form-row-group">
            <div class="form-row">
              <label>{{ t('Category') }}</label>
              <select v-model="recipeForm.category" class="input">
                <option value="Cocktail">{{ t('Cocktails') }}</option>
                <option value="Spirits & Shots">{{ t('Spirits & Shots') }}</option>
                <option value="Draft Beer">{{ t('Draft Beer') }}</option>
                <option value="Wine by the Glass">{{ t('Wine by the Glass') }}</option>
                <option value="Mocktail / Non-Alcoholic">{{ t('Mocktail / Non-Alcoholic') }}</option>
              </select>
            </div>
            <div class="form-row">
              <label>{{ t('Glassware') }}</label>
              <select v-model="recipeForm.glassware" class="input">
                <option value="Rocks Glass">{{ t('Rocks Glass') }}</option>
                <option value="Highball Glass">{{ t('Highball Glass') }}</option>
                <option value="Coupe Glass">{{ t('Coupe Glass') }}</option>
                <option value="Martini Glass">{{ t('Martini Glass') }}</option>
                <option value="Pint Glass">{{ t('Pint Glass') }}</option>
                <option value="Half Pint Glass">{{ t('Half Pint Glass') }}</option>
                <option value="Wine Glass">{{ t('Wine Glass') }}</option>
                <option value="Shot Glass">{{ t('Shot Glass') }}</option>
                <option value="Collins Glass">{{ t('Collins Glass') }}</option>
                <option value="Mug / Jar">{{ t('Mug / Jar') }}</option>
              </select>
            </div>
          </div>

          <div class="form-row">
            <label>{{ t('Total Serving Size (ml)') }}</label>
            <input v-model.number="recipeForm.serving_size_ml" type="number" class="input" placeholder="e.g. 150" />
          </div>

          <div class="form-row">
            <label>{{ t('Bartender Prep Instructions & Garnish') }}</label>
            <textarea
              v-model="recipeForm.prep_instructions"
              class="input textarea"
              rows="2"
              placeholder="e.g. Shake with ice for 15s, double strain, express orange peel..."
            />
          </div>

          <!-- INGREDIENTS BUILDER -->
          <div class="ing-section">
            <div class="ing-section-head">
              <label class="section-title">{{ t('Ingredients & Pour Ratios') }}</label>
              <button type="button" class="btn btn-sm btn-outline" @click="addIngredientRow">
                <Icon name="plus" :size="12" /> {{ t('Add Ingredient') }}
              </button>
            </div>

            <div v-if="!recipeForm.ingredients.length" class="muted small text-center p-2">
              {{ t('No ingredients added yet. Click "Add Ingredient".') }}
            </div>

            <div
              v-for="(ing, idx) in recipeForm.ingredients"
              :key="idx"
              class="ing-edit-row"
            >
              <input
                v-model="ing.ingredient_name"
                class="input ing-name-input"
                list="bar-items-datalist"
                :placeholder="t('Ingredient / Spirit from Item Master')"
              />
              <input
                v-model.number="ing.pour_qty"
                type="number"
                step="0.5"
                class="input ing-qty-input"
                placeholder="Qty"
              />
              <select v-model="ing.pour_uom" class="input ing-uom-select">
                <option value="ml">ml</option>
                <option value="oz">oz</option>
                <option value="cl">cl</option>
                <option value="dash">dash</option>
                <option value="splash">splash</option>
                <option value="bottle">bottle</option>
              </select>
              <label class="ing-base-check" :title="t('Mark as Base Spirit')">
                <input type="checkbox" v-model="ing.is_primary_spirit" />
                <span class="small">{{ t('Base') }}</span>
              </label>
              <button
                type="button"
                class="btn btn-sm btn-ghost btn-danger-icon"
                :title="t('Remove')"
                @click="removeIngredientRow(idx)"
              >
                <Icon name="close" :size="13" />
              </button>
            </div>
          </div>
        </div>

        <div class="modal-foot">
          <button
            v-if="recipeForm.name"
            type="button"
            class="btn btn-outline btn-danger-text me-auto"
            @click="deleteRecipeRecord"
          >
            {{ t('Delete Recipe') }}
          </button>
          <button type="button" class="btn btn-outline" @click="recipeModalOpen = false">{{ t('Cancel') }}</button>
          <button
            type="button"
            class="btn btn-primary"
            :disabled="saving || !recipeForm.recipe_name"
            @click="saveRecipeRecord"
          >
            {{ saving ? t('Saving…') : t('Save Recipe') }}
          </button>
        </div>
      </div>
    </div>

    <!-- MODAL: TAP / KEG EDIT -->
    <div v-if="editingTap" class="bar-modal-backdrop" @click.self="editingTap = null">
      <div class="bar-modal card">
        <div class="modal-head">
          <div class="modal-title">
            <Icon name="refresh" />
            <span>{{ tapModalAction === 'tap_new_keg' ? t('Tap New Keg') : t('Edit Tap Line') }}</span>
          </div>
          <button class="btn btn-ghost" @click="editingTap = null"><Icon name="close" /></button>
        </div>
        <div class="modal-body form-grid">
          <div class="form-row">
            <label>{{ t('Tap Identifier') }}</label>
            <input v-model="editingTap.tap_number" class="input" placeholder="e.g. Tap 01" />
          </div>
          <div class="form-row">
            <label>{{ t('Station') }}</label>
            <input v-model="editingTap.station" class="input" placeholder="e.g. Main Bar" />
          </div>
          <div class="form-row">
            <label>{{ t('Select Beverage / Keg from Item Master') }}</label>
            <select v-model="editingTap.keg_item" class="input" @change="onSelectTapItem">
              <option value="">-- {{ t('Choose Item from Master') }} --</option>
              <option v-for="it in menuItems" :key="it.item_code" :value="it.item_code">
                {{ it.item_name }} ({{ it.item_group }})
              </option>
            </select>
          </div>
          <div class="form-row">
            <label>{{ t('Keg Item Name / Brand Display') }}</label>
            <input v-model="editingTap.item_name" class="input" placeholder="e.g. House Wine Dispenser, Draft Beer" />
          </div>
          <div class="form-row-group">
            <div class="form-row">
              <label>{{ t('Unit of Measure') }}</label>
              <select v-model="editingTap.unit" class="input">
                <option value="ml">{{ t('ml (Milliliters - Liquor / Spirits / Wine)') }}</option>
                <option value="L">{{ t('L (Liters - Draft Beer Kegs)') }}</option>
              </select>
            </div>
            <div class="form-row">
              <label>{{ t('Status') }}</label>
              <select v-model="editingTap.status" class="input">
                <option value="Active">{{ t('Active') }}</option>
                <option value="Kicking Soon">{{ t('Kicking Soon') }}</option>
                <option value="Empty">{{ t('Empty') }}</option>
                <option value="Cleaning / Offline">{{ t('Cleaning / Offline') }}</option>
              </select>
            </div>
          </div>
          <div class="form-row-group">
            <div class="form-row">
              <label>{{ t('Capacity') }} ({{ editingTap.unit || 'ml' }})</label>
              <input v-model.number="editingTap.capacity_liters" type="number" class="input" />
            </div>
            <div v-if="tapModalAction !== 'tap_new_keg'" class="form-row">
              <label>{{ t('Remaining') }} ({{ editingTap.unit || 'ml' }})</label>
              <input v-model.number="editingTap.remaining_liters" type="number" class="input" />
            </div>
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn btn-outline" @click="editingTap = null">{{ t('Cancel') }}</button>
          <button class="btn btn-primary" :disabled="saving" @click="saveTapRecord">
            {{ saving ? t('Saving…') : t('Save Tap') }}
          </button>
        </div>
      </div>
    </div>

    <!-- MODAL: QUICK SPILLAGE ENTRY -->
    <div v-if="spillModalOpen" class="bar-modal-backdrop" @click.self="spillModalOpen = false">
      <div class="bar-modal card">
        <div class="modal-head">
          <div class="modal-title">
            <Icon name="warning" />
            <span>{{ t('Log Bar Spillage & Wastage') }}</span>
          </div>
          <button class="btn btn-ghost" @click="spillModalOpen = false"><Icon name="close" /></button>
        </div>
        <div class="modal-body form-grid">
          <div class="form-row">
            <label>{{ t('Reason') }}</label>
            <select v-model="spillForm.reason" class="input">
              <option value="Bad Pour / Foam Loss">{{ t('Bad Pour / Foam Loss') }}</option>
              <option value="Broken Bottle">{{ t('Broken Bottle') }}</option>
              <option value="Customer Return">{{ t('Customer Return / Remake') }}</option>
              <option value="Line Cleaning Flush">{{ t('Line Cleaning Flush') }}</option>
              <option value="Expired / Spoiled">{{ t('Expired / Spoiled') }}</option>
            </select>
          </div>
          <div class="form-row">
            <label>{{ t('Item / Spirit Code or Name') }}</label>
            <select v-model="spillForm.item_code" class="input" @change="onSelectSpillItem">
              <option value="">-- {{ t('Select Beverage / Spirit from Item Master') }} --</option>
              <optgroup v-if="taps.length" :label="t('Connected Bar Taps')">
                <option v-for="tap in taps" :key="tap.name" :value="tap.keg_item || tap.item_name">
                  {{ tap.tap_number }}: {{ tap.item_name }} ({{ formatVol(tap.remaining_liters) }} {{ tap.unit || 'ml' }} rem)
                </option>
              </optgroup>
              <optgroup :label="t('All Menu / Beverage Items')">
                <option v-for="it in menuItems" :key="it.item_code" :value="it.item_code">
                  {{ it.item_name }} ({{ it.item_group }})
                </option>
              </optgroup>
            </select>
          </div>
          <div class="form-row-group">
            <div class="form-row">
              <label>{{ t('Quantity Wasted') }}</label>
              <input v-model.number="spillForm.qty" type="number" step="0.1" class="input" />
            </div>
            <div class="form-row">
              <label>{{ t('Unit (UOM)') }}</label>
              <input v-model="spillForm.uom" class="input" placeholder="e.g. Nos, ml, Pint" />
            </div>
          </div>
          <div class="form-row">
            <label>{{ t('Incident Notes') }}</label>
            <textarea
              v-model="spillForm.notes"
              class="input textarea"
              rows="2"
              placeholder="Brief details about what happened…"
            />
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn btn-outline" @click="spillModalOpen = false">{{ t('Cancel') }}</button>
          <button class="btn btn-primary" :disabled="saving || !spillForm.item_code" @click="submitSpillage">
            {{ saving ? t('Logging…') : t('Log Spillage') }}
          </button>
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
const currentTab = ref('tickets') // 'tickets' | 'taps' | 'recipes' | 'spillage'

// Live tickets state
const tickets = ref([])
const avgSeconds = ref(0)
const loading = ref(true)
const now = ref(Date.now())
let clockSkew = 0
let poll = null
let ticker = null

// Taps state
const taps = ref([])
const editingTap = ref(null)
const tapModalAction = ref('edit')

// Menu Items from Item Master
const menuItems = ref([])
const selectedMenuItem = ref('')

// Recipes state
const recipes = ref([])
const recipeSearch = ref('')
const recipeCategory = ref('All')
const inspectedRecipe = ref(null)
const recipeModalOpen = ref(false)
const recipeForm = ref({
  name: '',
  recipe_name: '',
  item_code: '',
  category: 'Cocktail',
  glassware: 'Rocks Glass',
  serving_size_ml: 120,
  prep_instructions: '',
  ingredients: [],
})

// Spillage state
const spillages = ref([])
const todaySpillTotal = ref(0)
const spillModalOpen = ref(false)
const saving = ref(false)
const spillForm = ref({
  reason: 'Bad Pour / Foam Loss',
  item_code: '',
  qty: 30,
  uom: 'ml',
  notes: '',
})

const columns = computed(() => [
  { status: 'New', label: 'New orders', tickets: tickets.value.filter((x) => x.status === 'New') },
  { status: 'Preparing', label: 'Preparing', tickets: tickets.value.filter((x) => x.status === 'Preparing') },
  { status: 'Ready', label: 'Ready to hand over', tickets: tickets.value.filter((x) => x.status === 'Ready') },
])

const lowTapsCount = computed(() => {
  return taps.value.filter((t) => t.percent <= 15 && t.status !== 'Empty').length
})

const filteredRecipes = computed(() => {
  if (!recipeSearch.value) return recipes.value
  const s = recipeSearch.value.toLowerCase()
  return recipes.value.filter((r) =>
    (r.recipe_name || '').toLowerCase().includes(s) ||
    (r.item_code || '').toLowerCase().includes(s)
  )
})

const avgText = computed(() => {
  if (!avgSeconds.value) return ''
  const mins = Math.round(avgSeconds.value / 60)
  return mins < 1 ? t('under a minute') : t('{n} min', { n: mins })
})

function formatCurrency(val) {
  const num = Number(val) || 0
  return num.toFixed(2)
}

function formatVol(val) {
  if (val === null || val === undefined) return '0'
  const num = Number(val)
  if (isNaN(num)) return '0'
  if (Math.abs(num - Math.round(num)) < 0.01) {
    return Math.round(num).toLocaleString()
  }
  return num.toFixed(1)
}

function formatTimestamp(str) {
  if (!str) return '—'
  return String(str).split('.')[0].replace('T', ' ')
}

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

async function loadTickets() {
  if (session.offline) return
  try {
    const data = await call('lumen_restaurants.api.kitchen.board', {
      pos_profile: session.posProfile,
      station: 'Bar',
    })
    tickets.value = data.tickets || []
    avgSeconds.value = data.avg_seconds || 0
    if (data.now) clockSkew = Date.now() - serverTime(data.now)
  } catch (e) {
    session.notify(e.message, true)
  }
}

async function loadTaps() {
  if (session.offline) return
  try {
    const data = await call('lumen_restaurants.api.bar.get_bar_dashboard', {
      pos_profile: session.posProfile,
    })
    taps.value = data.taps || []
    todaySpillTotal.value = data.spillage_today?.total_cost || 0
  } catch (e) {
    session.notify(e.message, true)
  }
}

async function loadRecipes() {
  if (session.offline) return
  try {
    const data = await call('lumen_restaurants.api.bar.list_recipes', {
      category: recipeCategory.value,
    })
    recipes.value = data || []
  } catch (e) {
    session.notify(e.message, true)
  }
}

async function loadSpillages() {
  if (session.offline) return
  try {
    const data = await call('lumen_restaurants.api.bar.list_spillages', {
      pos_profile: session.posProfile,
    })
    spillages.value = data || []
  } catch (e) {
    session.notify(e.message, true)
  }
}

async function refreshCurrent() {
  loading.value = true
  if (currentTab.value === 'tickets') await loadTickets()
  else if (currentTab.value === 'taps') await Promise.all([loadTaps(), loadMenuItems()])
  else if (currentTab.value === 'recipes') await Promise.all([loadRecipes(), loadMenuItems()])
  else if (currentTab.value === 'spillage') await Promise.all([loadSpillages(), loadMenuItems()])
  loading.value = false
}

async function switchTab(tab) {
  currentTab.value = tab
  if (tab === 'tickets') loadTickets()
  else if (tab === 'taps') loadTaps()
  else if (tab === 'recipes') loadRecipes()
  else if (tab === 'spillage') loadSpillages()
}

async function advance(ticket, status) {
  try {
    await call('lumen_restaurants.api.kitchen.set_ticket_status', { name: ticket.name, status })
    await loadTickets()
  } catch (e) {
    session.notify(e.message, true)
  }
}

async function printSlip(ticket) {
  try {
    await call('lumen_restaurants.api.printing.print_bar_ticket', { ticket: ticket.name })
    session.notify(t('Slip sent to the bar printer'))
  } catch (e) {
    session.notify(e.message, true)
  }
}

async function inspectDrink(itemCode, itemName) {
  const code = itemCode || itemName
  if (!code) return
  try {
    const rec = await call('lumen_restaurants.api.bar.get_recipe', { item_code: code })
    if (rec) {
      inspectedRecipe.value = rec
    } else {
      inspectedRecipe.value = {
        recipe_name: itemName || itemCode,
        category: 'Standard Drink',
        glassware: 'Standard Glass',
        prep_instructions: t('Standard pour / single measure. No complex formulation registered.'),
        ingredients: [
          { ingredient_name: itemName || itemCode, pour_qty: 45, pour_uom: 'ml', is_primary_spirit: 1 }
        ],
      }
    }
  } catch (e) {
    session.notify(e.message, true)
  }
}

async function loadMenuItems() {
  try {
    const data = await call('lumen_restaurants.api.bar.get_beverage_items')
    menuItems.value = data || []
  } catch (e) {
    console.error('Failed to load menu items:', e)
  }
}

function onSelectMenuItem() {
  const found = menuItems.value.find((i) => i.item_code === selectedMenuItem.value)
  if (found) {
    recipeForm.value.recipe_name = found.item_name
    recipeForm.value.item_code = found.item_code
    if (found.item_group === 'Wine') recipeForm.value.category = 'Wine by the Glass'
  }
}

function onSelectTapItem() {
  const found = menuItems.value.find((i) => i.item_code === editingTap.value.keg_item)
  if (found) {
    editingTap.value.item_name = `${found.item_name} Dispenser`
    const m = (found.item_name || '').match(/(\d+)\s*ml/i)
    if (m) {
      editingTap.value.unit = 'ml'
      editingTap.value.capacity_liters = parseInt(m[1], 10)
      if (tapModalAction.value === 'tap_new_keg' || !editingTap.value.remaining_liters) {
        editingTap.value.remaining_liters = editingTap.value.capacity_liters
      }
    } else if (/(wine|liquor|whisky|whiskey|vodka|rum|gin|spirit|cocktail)/i.test(found.item_name || found.item_group || '')) {
      editingTap.value.unit = 'ml'
      if (!editingTap.value.capacity_liters || editingTap.value.capacity_liters <= 50) {
        editingTap.value.capacity_liters = 750
        editingTap.value.remaining_liters = 750
      }
    }
  }
}

function inspectRecipe(rec) {
  inspectedRecipe.value = rec
}

function openRecipeModal(rec = null) {
  if (rec) {
    selectedMenuItem.value = rec.item_code || ''
    recipeForm.value = {
      name: rec.name || '',
      recipe_name: rec.recipe_name || '',
      item_code: rec.item_code || rec.recipe_name || '',
      category: rec.category || 'Cocktail',
      glassware: rec.glassware || 'Rocks Glass',
      serving_size_ml: rec.serving_size_ml || 120,
      prep_instructions: rec.prep_instructions || '',
      ingredients: (rec.ingredients || []).map((i) => ({ ...i })),
    }
  } else {
    selectedMenuItem.value = ''
    recipeForm.value = {
      name: '',
      recipe_name: '',
      item_code: '',
      category: 'Cocktail',
      glassware: 'Rocks Glass',
      serving_size_ml: 120,
      prep_instructions: '',
      ingredients: [
        { ingredient_name: '', pour_qty: 45, pour_uom: 'ml', is_primary_spirit: 1 }
      ],
    }
  }
  recipeModalOpen.value = true
}

function editInspectedRecipe() {
  if (!inspectedRecipe.value) return
  const rec = inspectedRecipe.value
  inspectedRecipe.value = null
  openRecipeModal(rec)
}

function addIngredientRow() {
  recipeForm.value.ingredients.push({
    ingredient_name: '',
    pour_qty: 30,
    pour_uom: 'ml',
    is_primary_spirit: 0,
  })
}

function removeIngredientRow(idx) {
  recipeForm.value.ingredients.splice(idx, 1)
}

async function saveRecipeRecord() {
  if (!recipeForm.value.recipe_name) {
    session.notify(t('Drink Name is required'), true)
    return
  }
  saving.value = true
  try {
    const payload = {
      ...recipeForm.value,
      item_code: recipeForm.value.item_code || recipeForm.value.recipe_name,
    }
    await call('lumen_restaurants.api.bar.save_recipe', { payload })
    session.notify(t('Recipe saved successfully'))
    recipeModalOpen.value = false
    await loadRecipes()
  } catch (e) {
    session.notify(e.message, true)
  } finally {
    saving.value = false
  }
}

async function deleteRecipeRecord() {
  if (!recipeForm.value.name) return
  if (!confirm(t('Are you sure you want to delete this recipe?'))) return
  saving.value = true
  try {
    await call('lumen_restaurants.api.bar.delete_recipe', { name: recipeForm.value.name })
    session.notify(t('Recipe deleted'))
    recipeModalOpen.value = false
    await loadRecipes()
  } catch (e) {
    session.notify(e.message, true)
  } finally {
    saving.value = false
  }
}

function openTapModal(tap, action = 'edit') {
  tapModalAction.value = action
  if (tap) {
    editingTap.value = { ...tap, unit: tap.unit || 'ml' }
  } else {
    editingTap.value = {
      tap_number: `Tap ${String(taps.value.length + 1).padStart(2, '0')}`,
      station: 'Main Bar',
      item_name: '',
      unit: 'ml',
      capacity_liters: 750,
      remaining_liters: 750,
      status: 'Active',
    }
  }
}

async function saveTapRecord() {
  if (!editingTap.value) return
  saving.value = true
  try {
    await call('lumen_restaurants.api.bar.save_tap', {
      payload: { ...editingTap.value, action: tapModalAction.value }
    })
    session.notify(t('Tap updated successfully'))
    editingTap.value = null
    await loadTaps()
  } catch (e) {
    session.notify(e.message, true)
  } finally {
    saving.value = false
  }
}

function openSpillModal() {
  if (!menuItems.value.length) loadMenuItems()
  spillForm.value = {
    reason: 'Bad Pour / Foam Loss',
    item_code: '',
    item_name: '',
    qty: 30,
    uom: 'ml',
    notes: '',
  }
  spillModalOpen.value = true
}

function onSelectSpillItem() {
  const code = spillForm.value.item_code
  if (!code) return
  // Check active taps first
  const tap = taps.value.find((t) => (t.keg_item && t.keg_item === code) || t.item_name === code)
  if (tap) {
    spillForm.value.item_name = tap.item_name || tap.keg_item
    spillForm.value.uom = tap.unit || 'ml'
    return
  }
  // Check menu items
  const found = menuItems.value.find((i) => i.item_code === code)
  if (found) {
    spillForm.value.item_name = found.item_name
    const nameLower = (found.item_name || '').toLowerCase()
    if (nameLower.includes('ml') || ['Wine', 'Liquor', 'Beverages'].includes(found.item_group)) {
      spillForm.value.uom = 'ml'
    } else if (found.stock_uom) {
      spillForm.value.uom = found.stock_uom
    }
  }
}

async function submitSpillage() {
  if (!spillForm.value.item_code) return
  saving.value = true
  try {
    const found = menuItems.value.find((i) => i.item_code === spillForm.value.item_code)
    const tap = taps.value.find((t) => (t.keg_item && t.keg_item === spillForm.value.item_code) || t.item_name === spillForm.value.item_code)
    const itemName = spillForm.value.item_name || (found ? found.item_name : (tap ? tap.item_name : spillForm.value.item_code))
    await call('lumen_restaurants.api.bar.log_spillage', {
      payload: {
        pos_profile: session.posProfile,
        reason: spillForm.value.reason,
        notes: spillForm.value.notes,
        items: [{
          item_code: spillForm.value.item_code,
          item_name: itemName,
          qty: spillForm.value.qty,
          uom: spillForm.value.uom,
        }]
      }
    })
    session.notify(t('Spillage logged successfully'))
    spillModalOpen.value = false
    await loadSpillages()
  } catch (e) {
    session.notify(e.message, true)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  loading.value = true
  await Promise.all([loadTickets(), loadTaps(), loadMenuItems()])
  loading.value = false

  poll = setInterval(() => {
    loadTickets()
    if (currentTab.value === 'taps') {
      loadTaps()
    }
  }, 3000)
  ticker = setInterval(() => (now.value = Date.now()), 1000)
})

onUnmounted(() => {
  clearInterval(poll)
  clearInterval(ticker)
})
</script>

<style scoped>
.kds { flex: 1; display: flex; padding: 14px; overflow: hidden; }
.kds-card { flex: 1; display: flex; flex-direction: column; overflow: hidden; background: var(--card-bg); border-radius: 12px; }
.kds-head { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border-bottom: 1px solid var(--border); flex-wrap: wrap; }
.kds-title { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 16px; }

/* Bar Tab Switcher */
.bar-nav-tabs { display: flex; gap: 6px; background: var(--page-bg); padding: 4px; border-radius: 10px; margin-inline-end: auto; }
.bar-tab-btn {
  display: flex; align-items: center; gap: 6px; padding: 6px 14px; border: 0; background: transparent;
  font-size: 13px; font-weight: 600; color: var(--text-muted); border-radius: 8px; cursor: pointer; transition: all 0.15s ease;
}
.bar-tab-btn.active { background: var(--card-bg); color: var(--text); box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.tab-badge { background: var(--surface-2); border-radius: 999px; padding: 1px 7px; font-size: 11px; }
.tab-badge.warn { background: var(--red); color: #fff; }

.kpill { background: var(--surface-2); border-radius: 999px; padding: 4px 13px; font-size: 12.5px; color: var(--text-muted); }
.bar-action-btn { font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 6px; }

/* Live Tickets Grid */
.kcols { flex: 1; overflow: auto; display: grid; grid-template-columns: repeat(3, minmax(240px, 1fr)); gap: 12px; padding: 14px; background: var(--page-bg); align-content: start; }
.kcol h3 { font-size: 13.5px; margin: 0 4px 10px; color: var(--text-muted); display: flex; align-items: center; gap: 8px; }
.kcount { background: var(--card-bg); border: 1px solid var(--border); border-radius: 999px; padding: 0 10px; font-size: 12px; }
.kempty { padding: 40px 10px; text-align: center; }

.kticket {
  background: var(--card-bg); border: 1px solid var(--border); border-top: 4px solid var(--promo, #6d4aff);
  border-radius: 12px; padding: 12px; margin-bottom: 12px; box-shadow: var(--shadow);
}
.kticket.prep { border-top-color: var(--amber); }
.kticket.ready { border-top-color: var(--promo, #6d4aff); }
.khead { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
.kno { font-size: 24px; font-weight: 700; line-height: 1; }
.kno.table { font-size: 16px; }
.kbadge { font-size: 11px; font-weight: 700; border-radius: 6px; padding: 1px 8px; }
.kbadge.away { background: rgba(20, 99, 255, 0.1); color: var(--brand-dark); }
.kbadge.hall { background: rgba(109, 74, 255, 0.12); color: var(--promo); }
.ktimer { margin-inline-start: auto; font-size: 12px; font-weight: 700; border-radius: 999px; padding: 2px 10px; }
.ktimer.ok { background: rgba(109, 74, 255, 0.12); color: var(--promo); }
.ktimer.warn { background: rgba(201, 130, 27, 0.15); color: var(--amber); }
.ktimer.late { background: rgba(214, 69, 69, 0.13); color: var(--red); }

.kitems { margin: 0; padding: 0; list-style: none; font-size: 14.5px; }
.kitems li { padding: 5px 0; border-bottom: 1px dashed var(--border-subtle); }
.kitems li:last-child { border: 0; }
.kitem-main { display: flex; align-items: center; gap: 6px; cursor: pointer; }
.kitem-main:hover .drink-name { color: var(--promo, #6d4aff); }
.recipe-hint { color: var(--text-muted); opacity: 0.6; display: flex; }
.knote { display: inline-block; background: rgba(201, 130, 27, 0.14); color: var(--amber); border-radius: 6px; padding: 0 8px; font-size: 12px; margin-inline-start: 6px; }
.kmods { display: flex; flex-wrap: wrap; gap: 4px; margin: 5px 0 2px; padding-inline-start: 24px; }
.kmod { border-radius: 7px; padding: 2px 8px; font-size: 12.5px; font-weight: 700; background: var(--surface-2); color: var(--text); }
.kmod.add { background: color-mix(in srgb, var(--brand) 12%, transparent); color: var(--brand-dark); }
.kfree { margin-top: 4px; }
.kbtns { display: flex; gap: 8px; margin-top: 9px; }
.kbtn { flex: 1; border: 0; border-radius: 10px; padding: 10px; font: inherit; font-weight: 700; font-size: 13.5px; cursor: pointer; }
.kbtn.go, .kbtn.done { background: var(--promo, #6d4aff); color: #fff; }
.kbtn.hand { background: transparent; border: 1.5px solid var(--promo, #6d4aff); color: var(--promo, #6d4aff); }
.kbtn.print { flex: none; width: 44px; background: var(--surface-2); color: var(--text-muted); }
.kready-note { text-align: center; font-size: 12.5px; color: var(--promo, #6d4aff); font-weight: 700; margin-top: 7px; }

/* Panel Subviews (Taps, Recipes, Spillage) */
.bar-panel-view { flex: 1; overflow: auto; padding: 18px; display: flex; flex-direction: column; gap: 16px; background: var(--page-bg); }
.bar-panel-subhead { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
.panel-desc h3 { margin: 0 0 4px; font-size: 16px; font-weight: 700; }
.panel-desc p { margin: 0; }

/* Taps Grid */
.taps-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 16px; }
.tap-card {
  background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 16px;
  display: flex; flex-direction: column; gap: 12px; box-shadow: var(--shadow);
}
.tap-card.kicking { border-color: var(--amber); }
.tap-card.empty { border-color: var(--red); opacity: 0.8; }
.tap-head { display: flex; align-items: center; justify-content: space-between; }
.tap-no { font-weight: 800; font-size: 15px; }
.tap-station { font-size: 12px; }
.tap-badge { font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 6px; background: rgba(34, 197, 94, 0.12); color: #15803d; }
.tap-badge.kicking-soon { background: rgba(245, 158, 11, 0.15); color: #b45309; }
.tap-badge.empty { background: rgba(239, 68, 68, 0.15); color: #b91c1c; }
.tap-badge.cleaning---offline { background: var(--surface-2); color: var(--text-muted); }

.tap-beer-name { font-weight: 700; font-size: 15px; min-height: 40px; line-height: 1.3; }
.tap-vol-row { display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 6px; }
.tap-pct.warn { color: var(--red); font-weight: 700; }
.tap-gauge { width: 100%; height: 8px; background: var(--surface-2); border-radius: 999px; overflow: hidden; }
.tap-gauge-fill { height: 100%; background: #22c55e; border-radius: 999px; transition: width 0.3s ease; }
.tap-gauge-fill.warn { background: var(--amber); }
.tap-gauge-fill.critical { background: var(--red); }
.tap-actions { display: flex; gap: 8px; margin-top: auto; padding-top: 10px; border-top: 1px solid var(--border-subtle); align-items: center; }
.tap-btn { display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px; }
.tap-btn .icon { width: 14px; height: 14px; flex: none; }

/* Recipes Grid */
.recipe-filters { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.bar-search { max-width: 220px; font-size: 13px; }
.bar-cat-select { font-size: 13px; }
.recipes-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.recipe-card {
  background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 14px;
  display: flex; flex-direction: column; gap: 10px; cursor: pointer; transition: transform 0.12s, box-shadow 0.12s;
}
.recipe-card:hover { transform: translateY(-2px); box-shadow: var(--shadow); border-color: var(--promo, #6d4aff); }
.rec-top { display: flex; gap: 10px; align-items: center; }
.rec-glass-icon { width: 34px; height: 34px; border-radius: 8px; background: rgba(109, 74, 255, 0.1); color: var(--promo, #6d4aff); display: flex; align-items: center; justify-content: center; }
.rec-name { font-weight: 700; font-size: 15px; }
.rec-ingredients { display: flex; flex-direction: column; gap: 4px; font-size: 13px; background: var(--page-bg); padding: 8px 10px; border-radius: 8px; }
.rec-ing-row { display: flex; justify-content: space-between; }
.rec-prep-preview { font-style: italic; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* Spillage Table */
.spill-summary-pill { background: var(--card-bg); border: 1px solid var(--border); padding: 6px 14px; border-radius: 999px; font-size: 13px; display: flex; gap: 8px; align-items: center; }
.spill-table-wrap { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
.bar-table { width: 100%; border-collapse: collapse; font-size: 13.5px; text-align: left; }
.bar-table th { background: var(--surface-2); padding: 10px 14px; font-weight: 700; border-bottom: 1px solid var(--border); color: var(--text-muted); }
.bar-table td { padding: 10px 14px; border-bottom: 1px solid var(--border-subtle); vertical-align: top; }
.bar-table tr:last-child td { border-bottom: 0; }
.spill-reason-tag { background: rgba(239, 68, 68, 0.12); color: #dc2626; padding: 2px 8px; border-radius: 6px; font-weight: 600; font-size: 12px; }

/* Modals */
.bar-modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 16px; }
.bar-modal { width: 100%; max-width: 480px; max-height: 90vh; overflow-y: auto; background: var(--card-bg); border-radius: 14px; box-shadow: 0 10px 30px rgba(0,0,0,0.25); }
.modal-head { display: flex; align-items: center; justify-content: space-between; padding: 14px 18px; border-bottom: 1px solid var(--border); }
.modal-title { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 16px; }
.modal-body { padding: 18px; display: flex; flex-direction: column; gap: 14px; }
.modal-foot { display: flex; justify-content: flex-end; gap: 10px; padding: 14px 18px; border-top: 1px solid var(--border); }

.recipe-modal-badges { display: flex; gap: 8px; flex-wrap: wrap; }
.pill-badge { background: var(--promo, #6d4aff); color: #fff; padding: 3px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; }
.pill-badge.outline { background: transparent; border: 1px solid var(--border); color: var(--text); }
.section-title { font-size: 13.5px; font-weight: 700; margin: 4px 0 2px; }
.spec-ing-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 6px; font-size: 13.5px; }
.spec-ing-list li { display: flex; justify-content: space-between; padding: 6px 8px; background: var(--page-bg); border-radius: 8px; }
.primary-tag { font-size: 11px; background: rgba(109, 74, 255, 0.15); color: var(--promo, #6d4aff); padding: 1px 6px; border-radius: 4px; margin-inline-start: 6px; font-weight: normal; }
.spec-prep-box { background: var(--surface-2); padding: 12px; border-radius: 8px; font-size: 13.5px; line-height: 1.4; }

.form-grid { display: flex; flex-direction: column; gap: 12px; }
.form-row { display: flex; flex-direction: column; gap: 4px; }
.form-row label { font-size: 12.5px; font-weight: 600; color: var(--text-muted); }
.form-row-group { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }

/* Recipe Editor Styles */
.recipe-editor-modal { max-width: 580px; }
.rec-edit-btn { margin-inline-start: auto; padding: 4px 8px; font-size: 12px; }
.ing-section { display: flex; flex-direction: column; gap: 8px; background: var(--surface-2); padding: 12px; border-radius: 10px; margin-top: 4px; }
.ing-section-head { display: flex; justify-content: space-between; align-items: center; }
.ing-edit-row { display: flex; gap: 8px; align-items: center; }
.ing-name-input { flex: 2; font-size: 13px; }
.ing-qty-input { width: 75px; font-size: 13px; }
.ing-uom-select { width: 85px; font-size: 13px; }
.ing-base-check { display: flex; align-items: center; gap: 4px; font-size: 12px; white-space: nowrap; cursor: pointer; }
.btn-danger-icon { color: var(--red); padding: 4px 6px; }
.btn-danger-text { color: var(--red); border-color: rgba(239, 68, 68, 0.3); }
.me-auto { margin-inline-end: auto; }

@media (max-width: 900px) {
  .kcols { grid-template-columns: 1fr; }
  .bar-panel-subhead { flex-direction: column; align-items: flex-start; }
}
</style>
