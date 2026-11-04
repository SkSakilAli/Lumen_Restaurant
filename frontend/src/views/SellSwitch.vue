<!-- Copyright (c) 2026 Lumen Solutions
     SPDX-License-Identifier: AGPL-3.0-only
     "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md. -->
<!-- The same address, two tills: a restaurant outlet gets the restaurant
     screen, everyone else keeps the retail one. Split here so deep links and
     the rail never care which kind of outlet is signed in. -->
<template>
  <RestaurantSellView v-if="session.restaurantMode" />
  <SellView v-else />
</template>

<script setup>
import SellView from './SellView.vue'
import RestaurantSellView from './RestaurantSellView.vue'
import { useSessionStore } from '../stores/session'

const session = useSessionStore()
</script>
