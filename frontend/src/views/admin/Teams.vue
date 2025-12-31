<template>
  <div>
    <div class="d-flex align-center mb-4">
      <h1 class="text-h4">Teams</h1>
      <v-spacer />
      <v-btn color="primary" @click="openCreateDialog">
        <v-icon left>mdi-plus</v-icon>
        Add Team
      </v-btn>
    </div>

    <v-card>
      <v-data-table
        :headers="headers"
        :items="teams"
        :loading="loading"
      >
        <template #item.api_key_prefix="{ item }">
          <code>{{ item.api_key_prefix }}...</code>
        </template>
        <template #item.retention_days="{ item }">
          {{ item.retention_days ? `${item.retention_days} days` : 'Forever' }}
        </template>
        <template #item.created_at="{ item }">
          {{ formatDate(item.created_at) }}
        </template>
        <template #item.actions="{ item }">
          <v-btn icon variant="text" size="small" @click="openMembersDialog(item)">
            <v-icon>mdi-account-group</v-icon>
          </v-btn>
          <v-btn icon variant="text" size="small" @click="regenerateKey(item)">
            <v-icon>mdi-key-change</v-icon>
          </v-btn>
          <v-btn icon variant="text" size="small" @click="openEditDialog(item)">
            <v-icon>mdi-pencil</v-icon>
          </v-btn>
          <v-btn icon variant="text" size="small" color="error" @click="confirmDelete(item)">
            <v-icon>mdi-delete</v-icon>
          </v-btn>
        </template>
      </v-data-table>
    </v-card>

    <!-- Create/Edit Dialog -->
    <v-dialog v-model="dialog" max-width="500">
      <v-card>
        <v-card-title>{{ editingTeam ? 'Edit Team' : 'Create Team' }}</v-card-title>
        <v-card-text>
          <v-text-field v-model="form.name" label="Team Name" required />
          <v-text-field
            v-model.number="form.retention_days"
            label="Retention (days)"
            type="number"
            hint="Leave empty to keep logs forever"
            persistent-hint
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="dialog = false">Cancel</v-btn>
          <v-btn color="primary" :loading="saving" @click="saveTeam">Save</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- API Key Dialog -->
    <v-dialog v-model="keyDialog" max-width="600">
      <v-card>
        <v-card-title>API Key</v-card-title>
        <v-card-text>
          <v-alert type="warning" class="mb-4">
            This key will only be shown once. Copy it now!
          </v-alert>
          <v-text-field
            :model-value="newApiKey"
            label="API Key"
            readonly
            append-inner-icon="mdi-content-copy"
            @click:append-inner="copyKey"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="keyDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Members Dialog -->
    <v-dialog v-model="membersDialog" max-width="700">
      <v-card>
        <v-card-title>
          {{ selectedTeam?.name }} Members
        </v-card-title>
        <v-card-text>
          <v-data-table
            :headers="memberHeaders"
            :items="members"
            :loading="loadingMembers"
          >
            <template #item.role="{ item }">
              <v-chip size="small">{{ item.role }}</v-chip>
            </template>
            <template #item.actions="{ item }">
              <v-btn icon variant="text" size="small" color="error" @click="removeMember(item)">
                <v-icon>mdi-delete</v-icon>
              </v-btn>
            </template>
          </v-data-table>

          <v-divider class="my-4" />

          <h3 class="text-subtitle-1 mb-2">Add Member</h3>
          <v-row>
            <v-col cols="5">
              <v-select
                v-model="newMember.user_id"
                :items="availableUsers"
                item-title="name"
                item-value="id"
                label="User"
              />
            </v-col>
            <v-col cols="4">
              <v-select
                v-model="newMember.role"
                :items="['viewer', 'member', 'manager']"
                label="Role"
              />
            </v-col>
            <v-col cols="3" class="d-flex align-center">
              <v-btn color="primary" :disabled="!newMember.user_id" @click="addMember">
                Add
              </v-btn>
            </v-col>
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="membersDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation -->
    <v-dialog v-model="deleteDialog" max-width="400">
      <v-card>
        <v-card-title>Delete Team</v-card-title>
        <v-card-text>
          Are you sure you want to delete <strong>{{ teamToDelete?.name }}</strong>?
          This will also delete all logs for this team.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="deleteDialog = false">Cancel</v-btn>
          <v-btn color="error" :loading="deleting" @click="deleteTeam">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, reactive, computed } from 'vue'
import api, { type Team, type TeamMembership, type User } from '@/api/client'

const teams = ref<Team[]>([])
const users = ref<User[]>([])
const members = ref<TeamMembership[]>([])
const loading = ref(false)
const saving = ref(false)
const deleting = ref(false)
const loadingMembers = ref(false)

const dialog = ref(false)
const keyDialog = ref(false)
const membersDialog = ref(false)
const deleteDialog = ref(false)

const editingTeam = ref<Team | null>(null)
const selectedTeam = ref<Team | null>(null)
const teamToDelete = ref<Team | null>(null)
const newApiKey = ref('')

const form = reactive({
  name: '',
  retention_days: null as number | null,
})

const newMember = reactive({
  user_id: '',
  role: 'member',
})

const headers = [
  { title: 'Name', key: 'name' },
  { title: 'API Key', key: 'api_key_prefix' },
  { title: 'Retention', key: 'retention_days' },
  { title: 'Created', key: 'created_at' },
  { title: 'Actions', key: 'actions', sortable: false },
]

const memberHeaders = [
  { title: 'Name', key: 'user_name' },
  { title: 'Email', key: 'user_email' },
  { title: 'Role', key: 'role' },
  { title: 'Actions', key: 'actions', sortable: false },
]

const availableUsers = computed(() => {
  const memberIds = members.value.map(m => m.user_id)
  return users.value.filter(u => !memberIds.includes(u.id))
})

onMounted(async () => {
  await Promise.all([fetchTeams(), fetchUsers()])
})

async function fetchTeams() {
  loading.value = true
  try {
    const response = await api.get('/admin/teams')
    teams.value = response.data
  } catch (error) {
    console.error('Failed to fetch teams:', error)
  } finally {
    loading.value = false
  }
}

async function fetchUsers() {
  try {
    const response = await api.get('/admin/users')
    users.value = response.data
  } catch (error) {
    console.error('Failed to fetch users:', error)
  }
}

function openCreateDialog() {
  editingTeam.value = null
  form.name = ''
  form.retention_days = null
  dialog.value = true
}

function openEditDialog(team: Team) {
  editingTeam.value = team
  form.name = team.name
  form.retention_days = team.retention_days
  dialog.value = true
}

async function saveTeam() {
  saving.value = true
  try {
    if (editingTeam.value) {
      await api.put(`/admin/teams/${editingTeam.value.id}`, {
        name: form.name,
        retention_days: form.retention_days || null,
      })
      dialog.value = false
    } else {
      const response = await api.post('/admin/teams', {
        name: form.name,
        retention_days: form.retention_days || null,
      })
      dialog.value = false
      newApiKey.value = response.data.api_key
      keyDialog.value = true
    }
    await fetchTeams()
  } catch (error) {
    console.error('Failed to save team:', error)
  } finally {
    saving.value = false
  }
}

async function regenerateKey(team: Team) {
  try {
    const response = await api.post(`/admin/teams/${team.id}/regenerate-key`)
    newApiKey.value = response.data.api_key
    keyDialog.value = true
    await fetchTeams()
  } catch (error) {
    console.error('Failed to regenerate key:', error)
  }
}

function copyKey() {
  navigator.clipboard.writeText(newApiKey.value)
}

async function openMembersDialog(team: Team) {
  selectedTeam.value = team
  membersDialog.value = true
  loadingMembers.value = true
  try {
    const response = await api.get(`/admin/teams/${team.id}/members`)
    members.value = response.data
  } catch (error) {
    console.error('Failed to fetch members:', error)
  } finally {
    loadingMembers.value = false
  }
}

async function addMember() {
  if (!selectedTeam.value || !newMember.user_id) return
  try {
    await api.post(`/admin/teams/${selectedTeam.value.id}/members`, {
      user_id: newMember.user_id,
      role: newMember.role,
    })
    const response = await api.get(`/admin/teams/${selectedTeam.value.id}/members`)
    members.value = response.data
    newMember.user_id = ''
  } catch (error) {
    console.error('Failed to add member:', error)
  }
}

async function removeMember(member: TeamMembership) {
  if (!selectedTeam.value) return
  try {
    await api.delete(`/admin/teams/${selectedTeam.value.id}/members/${member.user_id}`)
    members.value = members.value.filter(m => m.id !== member.id)
  } catch (error) {
    console.error('Failed to remove member:', error)
  }
}

function confirmDelete(team: Team) {
  teamToDelete.value = team
  deleteDialog.value = true
}

async function deleteTeam() {
  if (!teamToDelete.value) return
  deleting.value = true
  try {
    await api.delete(`/admin/teams/${teamToDelete.value.id}`)
    deleteDialog.value = false
    await fetchTeams()
  } catch (error) {
    console.error('Failed to delete team:', error)
  } finally {
    deleting.value = false
  }
}

function formatDate(date: string) {
  return new Date(date).toLocaleDateString()
}
</script>
