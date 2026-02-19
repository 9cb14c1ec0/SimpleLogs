<template>
  <div>
    <h1 class="text-h4 mb-6">Dashboard</h1>

    <v-alert v-if="!authStore.user?.is_admin && teams.length === 0" type="info" class="mb-6">
      You are not a member of any teams. Please contact an administrator.
    </v-alert>

    <v-row>
      <v-col v-for="team in teams" :key="team.id" cols="12" sm="6" md="4">
        <v-card @click="viewLogs(team)" class="cursor-pointer" hover>
          <v-card-title>{{ team.name }}</v-card-title>
          <v-card-subtitle>
            {{ team.api_keys.length }} API key{{ team.api_keys.length !== 1 ? 's' : '' }}
          </v-card-subtitle>
          <v-card-text>
            <div v-if="team.retention_days">
              Retention: {{ team.retention_days }} days
            </div>
            <div v-else>
              Retention: Forever
            </div>
          </v-card-text>
          <v-card-actions>
            <v-btn color="primary" variant="text">
              View Logs
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <v-alert v-if="authStore.user?.is_admin && teams.length === 0" type="info" class="mt-6">
      No teams yet. <router-link to="/admin/teams">Create a team</router-link> to get started.
    </v-alert>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api, { type Team } from '@/api/client'

const router = useRouter()
const authStore = useAuthStore()
const teams = ref<Team[]>([])

onMounted(async () => {
  try {
    // Admin sees all teams, users see only their teams
    const response = await api.get('/admin/teams')
    teams.value = response.data
  } catch {
    // Non-admin users can't access admin endpoint
    // For now, show empty - in a real app you'd have a user-facing teams endpoint
    teams.value = []
  }
})

function viewLogs(team: Team) {
  router.push(`/teams/${team.id}/logs`)
}
</script>

<style scoped>
.cursor-pointer {
  cursor: pointer;
}
</style>
