<template>
  <div>
    <div class="d-flex align-center mb-4">
      <h1 class="text-h4">Users</h1>
      <v-spacer />
      <v-btn color="primary" @click="openCreateDialog">
        <v-icon left>mdi-plus</v-icon>
        Add User
      </v-btn>
    </div>

    <v-card>
      <v-data-table
        :headers="headers"
        :items="users"
        :loading="loading"
      >
        <template #item.is_admin="{ item }">
          <v-chip :color="item.is_admin ? 'primary' : 'grey'" size="small">
            {{ item.is_admin ? 'Admin' : 'User' }}
          </v-chip>
        </template>
        <template #item.is_active="{ item }">
          <v-chip :color="item.is_active ? 'success' : 'error'" size="small">
            {{ item.is_active ? 'Active' : 'Inactive' }}
          </v-chip>
        </template>
        <template #item.created_at="{ item }">
          {{ formatDate(item.created_at) }}
        </template>
        <template #item.actions="{ item }">
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
        <v-card-title>{{ editingUser ? 'Edit User' : 'Create User' }}</v-card-title>
        <v-card-text>
          <v-text-field v-model="form.name" label="Name" required />
          <v-text-field v-model="form.email" label="Email" type="email" required />
          <v-text-field
            v-model="form.password"
            label="Password"
            type="password"
            :hint="editingUser ? 'Leave blank to keep current password' : ''"
            :required="!editingUser"
          />
          <v-switch v-model="form.is_admin" label="Admin" color="primary" />
          <v-switch v-if="editingUser" v-model="form.is_active" label="Active" color="success" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="dialog = false">Cancel</v-btn>
          <v-btn color="primary" :loading="saving" @click="saveUser">Save</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation -->
    <v-dialog v-model="deleteDialog" max-width="400">
      <v-card>
        <v-card-title>Delete User</v-card-title>
        <v-card-text>
          Are you sure you want to delete <strong>{{ userToDelete?.name }}</strong>?
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="deleteDialog = false">Cancel</v-btn>
          <v-btn color="error" :loading="deleting" @click="deleteUser">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, reactive } from 'vue'
import api, { type User } from '@/api/client'

const users = ref<User[]>([])
const loading = ref(false)
const saving = ref(false)
const deleting = ref(false)

const dialog = ref(false)
const deleteDialog = ref(false)
const editingUser = ref<User | null>(null)
const userToDelete = ref<User | null>(null)

const form = reactive({
  name: '',
  email: '',
  password: '',
  is_admin: false,
  is_active: true,
})

const headers = [
  { title: 'Name', key: 'name' },
  { title: 'Email', key: 'email' },
  { title: 'Role', key: 'is_admin' },
  { title: 'Status', key: 'is_active' },
  { title: 'Created', key: 'created_at' },
  { title: 'Actions', key: 'actions', sortable: false },
]

onMounted(fetchUsers)

async function fetchUsers() {
  loading.value = true
  try {
    const response = await api.get('/admin/users')
    users.value = response.data
  } catch (error) {
    console.error('Failed to fetch users:', error)
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  editingUser.value = null
  form.name = ''
  form.email = ''
  form.password = ''
  form.is_admin = false
  form.is_active = true
  dialog.value = true
}

function openEditDialog(user: User) {
  editingUser.value = user
  form.name = user.name
  form.email = user.email
  form.password = ''
  form.is_admin = user.is_admin
  form.is_active = user.is_active
  dialog.value = true
}

async function saveUser() {
  saving.value = true
  try {
    if (editingUser.value) {
      const data: Record<string, unknown> = {
        name: form.name,
        email: form.email,
        is_admin: form.is_admin,
        is_active: form.is_active,
      }
      if (form.password) {
        data.password = form.password
      }
      await api.put(`/admin/users/${editingUser.value.id}`, data)
    } else {
      await api.post('/admin/users', {
        name: form.name,
        email: form.email,
        password: form.password,
        is_admin: form.is_admin,
      })
    }
    dialog.value = false
    await fetchUsers()
  } catch (error) {
    console.error('Failed to save user:', error)
  } finally {
    saving.value = false
  }
}

function confirmDelete(user: User) {
  userToDelete.value = user
  deleteDialog.value = true
}

async function deleteUser() {
  if (!userToDelete.value) return
  deleting.value = true
  try {
    await api.delete(`/admin/users/${userToDelete.value.id}`)
    deleteDialog.value = false
    await fetchUsers()
  } catch (error) {
    console.error('Failed to delete user:', error)
  } finally {
    deleting.value = false
  }
}

function formatDate(date: string) {
  return new Date(date).toLocaleDateString()
}
</script>
