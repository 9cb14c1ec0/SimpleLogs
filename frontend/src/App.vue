<template>
  <v-app>
    <v-navigation-drawer
      v-if="authStore.isAuthenticated"
      v-model:rail="rail"
      :width="216"
      permanent
    >
      <template #prepend>
        <div class="brand">
          <v-btn
            icon="mdi-menu"
            variant="text"
            size="small"
            :title="rail ? 'Expand sidebar' : 'Collapse sidebar'"
            @click.stop="rail = !rail"
          />
          <span v-if="!rail" class="brand__name">SimpleLogs</span>
        </div>
        <v-divider />
      </template>

      <v-list density="compact" nav>
        <v-list-item prepend-icon="mdi-view-dashboard" title="Dashboard" to="/" />

        <v-list-subheader v-if="authStore.user?.is_admin && !rail">Admin</v-list-subheader>
        <template v-if="authStore.user?.is_admin">
          <v-list-item prepend-icon="mdi-account-group" title="Users" to="/admin/users" />
          <v-list-item prepend-icon="mdi-account-multiple" title="Teams" to="/admin/teams" />
        </template>
      </v-list>

      <template #append>
        <v-divider />
        <v-menu location="top end">
          <template #activator="{ props }">
            <v-list density="compact" nav class="py-1">
              <v-list-item
                v-bind="props"
                prepend-icon="mdi-account-circle"
                :title="authStore.user?.name"
                :subtitle="authStore.user?.email"
              />
            </v-list>
          </template>
          <v-list density="compact">
            <v-list-item prepend-icon="mdi-cog" title="Settings" to="/settings" />
            <v-list-item prepend-icon="mdi-logout" title="Log out" @click="logout" />
          </v-list>
        </v-menu>
      </template>
    </v-navigation-drawer>

    <v-app-bar v-if="authStore.isAuthenticated" flat :height="52" border="b">
      <v-btn
        v-if="pageHeader.back"
        icon="mdi-arrow-left"
        variant="text"
        size="small"
        class="ml-2"
        :to="pageHeader.back"
      />
      <div class="pagehead" :class="{ 'ml-4': !pageHeader.back }">
        <span class="pagehead__title">{{ pageHeader.title || routeTitle }}</span>
        <span v-if="pageHeader.meta" class="pagehead__meta">{{ pageHeader.meta }}</span>
      </div>
    </v-app-bar>

    <v-main :class="{ 'main--fill': fullBleed }">
      <v-container fluid :class="fullBleed ? 'pa-0 h-100' : ''">
        <router-view />
      </v-container>
    </v-main>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000">
      {{ snackbar.message }}
    </v-snackbar>
  </v-app>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { pageHeader } from '@/composables/usePageHeader'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const rail = ref(false)

// Routes that manage their own height instead of growing the page
const fullBleed = computed(() => route.meta.fullBleed === true)

// Fallback heading for views that don't set one
const routeTitles: Record<string, string> = {
  dashboard: 'Dashboard',
  analytics: 'Analytics',
  settings: 'Settings',
  'admin-users': 'Users',
  'admin-teams': 'Teams',
}
const routeTitle = computed(() => routeTitles[route.name as string] ?? '')

const snackbar = reactive({
  show: false,
  message: '',
  color: 'success',
})

async function logout() {
  await authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
/* v-main is border-box with padding-top for the app bar, so a fixed height
   leaves the content box at exactly the remaining viewport. */
.main--fill {
  height: 100dvh;
  overflow: hidden;
}

.brand {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 51px;
  padding: 0 8px;
}

.brand__name {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.pagehead {
  display: flex;
  align-items: baseline;
  gap: 10px;
  min-width: 0;
}

.pagehead__title {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.01em;
  white-space: nowrap;
}

.pagehead__meta {
  font-family: ui-monospace, 'Cascadia Mono', 'SF Mono', Menlo, Consolas, monospace;
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  opacity: 0.5;
  white-space: nowrap;
}
</style>
