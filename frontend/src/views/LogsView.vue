<template>
  <div>
    <div class="d-flex align-center mb-4">
      <v-btn icon variant="text" @click="router.push('/')">
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
      <h1 class="text-h4 ml-2">{{ teamName }} Logs</h1>
    </div>

    <!-- Search Filters -->
    <v-card class="mb-4">
      <v-card-text>
        <v-row>
          <v-col cols="12" md="4">
            <v-text-field
              v-model="search.q"
              label="Search messages"
              prepend-inner-icon="mdi-magnify"
              clearable
              @keyup.enter="fetchLogs"
            />
          </v-col>
          <v-col cols="12" md="2">
            <v-select
              v-model="search.levels"
              :items="levelOptions"
              label="Level"
              multiple
              clearable
              chips
            />
          </v-col>
          <v-col cols="12" md="2">
            <v-text-field
              v-model="search.source"
              label="Source"
              clearable
            />
          </v-col>
          <v-col cols="12" md="2">
            <v-text-field
              v-model="search.from"
              label="From"
              type="datetime-local"
            />
          </v-col>
          <v-col cols="12" md="2">
            <v-text-field
              v-model="search.to"
              label="To"
              type="datetime-local"
            />
          </v-col>
        </v-row>
        <v-row>
          <v-col cols="12" md="6">
            <v-text-field
              v-model="search.metadataFilter"
              label="Metadata filter (e.g., user_id=123)"
              hint="Format: field=value"
              clearable
            />
          </v-col>
          <v-col cols="12" md="6" class="d-flex align-center">
            <v-btn color="primary" @click="fetchLogs">
              Search
            </v-btn>
            <v-btn class="ml-2" variant="text" @click="resetFilters">
              Reset
            </v-btn>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Column Settings -->
    <div class="d-flex justify-end mb-2" v-if="availableMetadataKeys.length > 0">
      <v-menu v-model="columnMenuOpen" :close-on-content-click="false" location="bottom end">
        <template #activator="{ props }">
          <v-btn v-bind="props" variant="outlined" size="small" prepend-icon="mdi-table-column">
            Columns
            <v-badge
              v-if="selectedMetadataColumns.length > 0"
              :content="selectedMetadataColumns.length"
              color="primary"
              inline
              class="ml-1"
            />
          </v-btn>
        </template>
        <v-card min-width="250">
          <v-card-title class="text-subtitle-1 pb-0">Metadata Columns</v-card-title>
          <v-card-text class="pb-0">
            <div class="d-flex gap-2 mb-2">
              <v-btn size="x-small" variant="text" @click="selectAllColumns">Select all</v-btn>
              <v-btn size="x-small" variant="text" @click="clearAllColumns">Clear all</v-btn>
            </div>
            <v-divider class="mb-2" />
            <v-list density="compact" class="py-0">
              <v-list-item
                v-for="key in availableMetadataKeys"
                :key="key"
                @click="toggleMetadataColumn(key)"
                class="px-0"
              >
                <template #prepend>
                  <v-checkbox-btn
                    :model-value="isColumnSelected(key)"
                    @click.stop="toggleMetadataColumn(key)"
                  />
                </template>
                <v-list-item-title class="text-body-2">{{ key }}</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn size="small" @click="columnMenuOpen = false">Done</v-btn>
          </v-card-actions>
        </v-card>
      </v-menu>
    </div>

    <!-- Logs Table -->
    <v-card>
      <v-data-table-server
        v-model:items-per-page="itemsPerPage"
        v-model:page="page"
        :headers="headers"
        :items="logs"
        :items-length="totalLogs"
        :loading="loading"
        class="elevation-1"
        @update:options="onTableUpdate"
      >
        <template #item.timestamp="{ item }">
          {{ formatDate(item.timestamp) }}
        </template>
        <template #item.level="{ item }">
          <v-chip :color="getLevelColor(item.level)" size="small">
            {{ item.level.toUpperCase() }}
          </v-chip>
        </template>
        <template #item.message="{ item }">
          <div class="text-truncate" style="max-width: 400px;">
            {{ item.message }}
          </div>
        </template>
        <template
          v-for="key in selectedMetadataColumns"
          :key="key"
          #[`item.metadata.${key}`]="{ item }"
        >
          <div class="text-truncate metadata-cell">
            {{ getMetadataValue(item, key) }}
          </div>
        </template>
        <template #item.metadata="{ item }">
          <v-chip v-if="item.metadata" size="small" @click="showMetadata(item)">
            View
          </v-chip>
          <span v-else>-</span>
        </template>
      </v-data-table-server>
    </v-card>

    <!-- Metadata Dialog -->
    <v-dialog v-model="metadataDialog" max-width="600">
      <v-card>
        <v-card-title>Log Details</v-card-title>
        <v-card-text>
          <pre class="text-body-2">{{ JSON.stringify(selectedLog, null, 2) }}</pre>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="metadataDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, reactive, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api, { type Log } from '@/api/client'

const route = useRoute()
const router = useRouter()

const teamId = route.params.teamId as string
const teamName = ref('')
const logs = ref<Log[]>([])
const totalLogs = ref(0)
const loading = ref(false)
const page = ref(1)
const itemsPerPage = ref(50)

const metadataDialog = ref(false)
const selectedLog = ref<Log | null>(null)
const columnMenuOpen = ref(false)

// Metadata columns state
const availableMetadataKeys = ref<string[]>([])
const selectedMetadataColumns = ref<string[]>([])

// LocalStorage key for persisting column preferences
const storageKey = `simplelogs-metadata-columns-${teamId}`

// Load saved column preferences from localStorage
function loadColumnPreferences() {
  try {
    const saved = localStorage.getItem(storageKey)
    if (saved) {
      selectedMetadataColumns.value = JSON.parse(saved)
    }
  } catch {
    // Ignore parse errors
  }
}

// Save column preferences to localStorage
function saveColumnPreferences() {
  localStorage.setItem(storageKey, JSON.stringify(selectedMetadataColumns.value))
}

// Watch for changes to selected columns and persist
watch(selectedMetadataColumns, saveColumnPreferences, { deep: true })

// Extract unique metadata keys from logs
function extractMetadataKeys(logItems: Log[]): string[] {
  const keys = new Set<string>()
  logItems.forEach(log => {
    if (log.metadata) {
      Object.keys(log.metadata).forEach(key => keys.add(key))
    }
  })
  return Array.from(keys).sort()
}

// Toggle a metadata column
function toggleMetadataColumn(key: string) {
  const index = selectedMetadataColumns.value.indexOf(key)
  if (index === -1) {
    selectedMetadataColumns.value.push(key)
  } else {
    selectedMetadataColumns.value.splice(index, 1)
  }
}

// Check if a metadata column is selected
function isColumnSelected(key: string): boolean {
  return selectedMetadataColumns.value.includes(key)
}

// Select all metadata columns
function selectAllColumns() {
  selectedMetadataColumns.value = [...availableMetadataKeys.value]
}

// Clear all metadata columns
function clearAllColumns() {
  selectedMetadataColumns.value = []
}

// Get display value for a metadata field
function getMetadataValue(log: Log, key: string): string {
  if (!log.metadata || !(key in log.metadata)) {
    return '-'
  }
  const value = log.metadata[key]
  if (value === null || value === undefined) {
    return '-'
  }
  if (typeof value === 'object') {
    return JSON.stringify(value)
  }
  return String(value)
}

const search = reactive({
  q: '',
  levels: [] as string[],
  source: '',
  from: '',
  to: '',
  metadataFilter: '',
})

const levelOptions = ['debug', 'info', 'warn', 'error', 'fatal']

const baseHeaders = [
  { title: 'Timestamp', key: 'timestamp', width: '180px' },
  { title: 'Level', key: 'level', width: '100px' },
  { title: 'Source', key: 'source', width: '120px' },
  { title: 'Message', key: 'message' },
]

const metadataHeader = { title: 'Metadata', key: 'metadata', width: '100px', sortable: false }

const headers = computed(() => {
  const metadataColumns = selectedMetadataColumns.value.map(key => ({
    title: key,
    key: `metadata.${key}`,
    width: '150px',
    sortable: false,
  }))
  return [...baseHeaders, ...metadataColumns, metadataHeader]
})

onMounted(async () => {
  loadColumnPreferences()
  try {
    const response = await api.get(`/admin/teams/${teamId}`)
    teamName.value = response.data.name
  } catch {
    teamName.value = 'Unknown Team'
  }
  fetchLogs()
})

async function fetchLogs() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    params.append('page', page.value.toString())
    params.append('limit', itemsPerPage.value.toString())

    if (search.q) params.append('q', search.q)
    if (search.source) params.append('source', search.source)
    if (search.from) params.append('from', new Date(search.from).toISOString())
    if (search.to) params.append('to', new Date(search.to).toISOString())
    search.levels.forEach(level => params.append('level', level))

    // Parse metadata filter
    if (search.metadataFilter) {
      const parts = search.metadataFilter.split('=')
      if (parts.length === 2) {
        params.append(`metadata.${parts[0].trim()}`, parts[1].trim())
      }
    }

    const response = await api.get(`/teams/${teamId}/logs?${params.toString()}`)
    logs.value = response.data.items
    totalLogs.value = response.data.total

    // Extract available metadata keys from fetched logs
    const newKeys = extractMetadataKeys(response.data.items)
    // Merge with existing keys to preserve previously seen keys
    const allKeys = new Set([...availableMetadataKeys.value, ...newKeys])
    availableMetadataKeys.value = Array.from(allKeys).sort()
  } catch (error) {
    console.error('Failed to fetch logs:', error)
  } finally {
    loading.value = false
  }
}

function onTableUpdate(options: { page: number; itemsPerPage: number }) {
  page.value = options.page
  itemsPerPage.value = options.itemsPerPage
  fetchLogs()
}

function resetFilters() {
  search.q = ''
  search.levels = []
  search.source = ''
  search.from = ''
  search.to = ''
  search.metadataFilter = ''
  page.value = 1
  fetchLogs()
}

function formatDate(date: string) {
  return new Date(date).toLocaleString()
}

function getLevelColor(level: string) {
  const colors: Record<string, string> = {
    debug: 'grey',
    info: 'blue',
    warn: 'orange',
    error: 'red',
    fatal: 'purple',
  }
  return colors[level] || 'grey'
}

function showMetadata(log: Log) {
  selectedLog.value = log
  metadataDialog.value = true
}
</script>

<style scoped>
pre {
  white-space: pre-wrap;
  word-wrap: break-word;
}

.metadata-cell {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
