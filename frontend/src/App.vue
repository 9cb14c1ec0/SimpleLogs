<template>
  <v-app>
    <v-navigation-drawer v-if="authStore.isAuthenticated" v-model="drawer" app>
      <v-list density="compact" nav>
        <v-list-item prepend-icon="mdi-view-dashboard" title="Dashboard" to="/" />

        <v-list-subheader v-if="authStore.user?.is_admin">Admin</v-list-subheader>
        <template v-if="authStore.user?.is_admin">
          <v-list-item prepend-icon="mdi-account-group" title="Users" to="/admin/users" />
          <v-list-item prepend-icon="mdi-account-multiple" title="Teams" to="/admin/teams" />
        </template>
      </v-list>
    </v-navigation-drawer>

    <v-app-bar v-if="authStore.isAuthenticated" app>
      <v-app-bar-nav-icon @click="drawer = !drawer" />
      <v-toolbar-title>SimpleLogs</v-toolbar-title>

      <v-spacer />

      <v-menu>
        <template #activator="{ props }">
          <v-btn icon v-bind="props">
            <v-icon>mdi-account-circle</v-icon>
          </v-btn>
        </template>
        <v-list>
          <v-list-item>
            <v-list-item-title>{{ authStore.user?.name }}</v-list-item-title>
            <v-list-item-subtitle>{{ authStore.user?.email }}</v-list-item-subtitle>
          </v-list-item>
          <v-divider />
          <v-list-item to="/settings">
            <v-list-item-title>Settings</v-list-item-title>
          </v-list-item>
          <v-list-item @click="logout">
            <v-list-item-title>Logout</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
    </v-app-bar>

    <v-main>
      <v-container fluid>
        <router-view />
      </v-container>
    </v-main>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000">
      {{ snackbar.message }}
    </v-snackbar>
  </v-app>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const drawer = ref(true)

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
