<template>
  <div>
    <div class="d-flex align-center mb-4">
      <v-btn icon variant="text" @click="router.push('/')">
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
      <h1 class="text-h4 ml-2">{{ teamName }} Logs</h1>
      <v-spacer />
      <v-btn
        variant="tonal"
        prepend-icon="mdi-chart-bar"
        :to="`/teams/${teamId}/analytics`"
      >
        Analytics
      </v-btn>
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
              v-model="search.userId"
              label="User ID"
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
        </v-row>
        <v-row>
          <v-col cols="12" md="2">
            <v-text-field
              v-model="search.to"
              label="To"
              type="datetime-local"
            />
          </v-col>
          <v-col cols="12" md="4">
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

    <!-- Column Settings & Export -->
    <div class="d-flex justify-end mb-2 gap-2">
      <v-btn
        variant="outlined"
        size="small"
        prepend-icon="mdi-database-sync"
        @click="backfillDialog = true"
      >
        Backfill User ID
      </v-btn>
      <v-btn
        variant="outlined"
        size="small"
        prepend-icon="mdi-file-delimited-outline"
        @click="openExportDialog"
        :disabled="logs.length === 0"
      >
        Export CSV
      </v-btn>
      <v-menu v-model="columnMenuOpen" :close-on-content-click="false" location="bottom end">
        <template #activator="{ props }">
          <v-btn v-bind="props" variant="outlined" size="small" prepend-icon="mdi-table-column">
            Columns
          </v-btn>
        </template>
        <v-card min-width="280" max-height="400" class="overflow-auto">
          <!-- Standard Columns Section -->
          <v-card-title class="text-subtitle-1 pb-0">Standard Columns</v-card-title>
          <v-card-text class="pb-0">
            <div class="d-flex gap-2 mb-2">
              <v-btn size="x-small" variant="text" @click="showAllStandardColumns">Show all</v-btn>
              <v-btn size="x-small" variant="text" @click="hideAllStandardColumns">Hide all</v-btn>
            </div>
            <v-list density="compact" class="py-0">
              <v-list-item
                v-for="key in standardColumnKeys"
                :key="key"
                @click="toggleStandardColumn(key)"
                class="px-0"
              >
                <template #prepend>
                  <v-checkbox-btn
                    :model-value="isStandardColumnVisible(key)"
                    @click.stop="toggleStandardColumn(key)"
                  />
                </template>
                <v-list-item-title class="text-body-2 text-capitalize">{{ key }}</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-card-text>

          <!-- Metadata Columns Section -->
          <template v-if="availableMetadataKeys.length > 0">
            <v-divider class="my-2" />
            <v-card-title class="text-subtitle-1 pb-0">Metadata Columns</v-card-title>
            <v-card-text class="pb-0">
              <div class="d-flex gap-2 mb-2">
                <v-btn size="x-small" variant="text" @click="selectAllMetadataColumns">Select all</v-btn>
                <v-btn size="x-small" variant="text" @click="clearAllMetadataColumns">Clear all</v-btn>
              </div>
              <v-list density="compact" class="py-0">
                <v-list-item
                  v-for="key in availableMetadataKeys"
                  :key="key"
                  @click="toggleMetadataColumn(key)"
                  class="px-0"
                >
                  <template #prepend>
                    <v-checkbox-btn
                      :model-value="isMetadataColumnSelected(key)"
                      @click.stop="toggleMetadataColumn(key)"
                    />
                  </template>
                  <v-list-item-title class="text-body-2">{{ key }}</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-card-text>
          </template>

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
        <template #item.user_id="{ item }">
          <span>{{ item.user_id || '-' }}</span>
        </template>
        <template #item.metadata="{ item }">
          <div v-if="item.metadata" class="d-flex align-center ga-1">
            <v-chip size="small" @click="showMetadata(item)">
              View
            </v-chip>
            <v-btn
              icon="mdi-content-copy"
              size="x-small"
              variant="text"
              title="Copy metadata JSON"
              @click="copyMetadata(item)"
            />
          </div>
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

    <!-- Backfill Dialog -->
    <v-dialog v-model="backfillDialog" max-width="500">
      <v-card>
        <v-card-title>Backfill User ID</v-card-title>
        <v-card-text>
          <p class="mb-4">
            Copy a metadata key into the <code>user_id</code> column for all logs in this team.
          </p>
          <v-text-field
            v-model="backfillKey"
            label="Metadata key"
            hint="e.g. user_id, userId, user"
            persistent-hint
          />
          <v-checkbox
            v-model="backfillOverwrite"
            label="Overwrite existing user_id values"
            density="compact"
            class="mt-2"
          />
          <v-alert v-if="backfillResult" :type="backfillError ? 'error' : 'success'" class="mt-2">
            {{ backfillResult }}
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="backfillDialog = false">Close</v-btn>
          <v-btn
            color="primary"
            :loading="backfillLoading"
            :disabled="!backfillKey"
            @click="runBackfill"
          >
            Run Backfill
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Export Dialog -->
    <v-dialog v-model="exportDialog" max-width="520" :persistent="exporting">
      <v-card>
        <v-card-title>Export CSV</v-card-title>
        <v-card-text>
          <p class="mb-2">
            Your current filters match
            <strong>{{ totalLogs.toLocaleString() }}</strong>
            {{ totalLogs === 1 ? 'entry' : 'entries' }}
            <span v-if="estimatedExportBytes">(approx. {{ formatBytes(estimatedExportBytes) }})</span>
            across {{ exportColumns().length }} columns.
          </p>

          <v-alert v-if="exportTooLarge" type="error" density="compact" class="mb-2">
            That is above the {{ EXPORT_MAX_ROWS.toLocaleString() }} row export limit. Narrow the
            filters (tighter date range or level) before exporting everything, or export just this
            page.
          </v-alert>
          <v-alert v-else-if="exportNeedsWarning" type="warning" density="compact" class="mb-2">
            This is a large export. It is built in the browser, so it may take a while and use a lot
            of memory. Narrowing the filters first is usually faster.
          </v-alert>

          <v-checkbox
            v-model="exportIncludeMetadata"
            label="Include full metadata as a JSON column"
            density="compact"
            hide-details
            :disabled="exporting"
          />

          <div v-if="exporting" class="mt-4">
            <v-progress-linear
              :model-value="totalLogs ? (exportedRows / Math.min(totalLogs, EXPORT_MAX_ROWS)) * 100 : 0"
              height="6"
              rounded
            />
            <div class="text-caption mt-1">
              Fetched {{ exportedRows.toLocaleString() }} rows...
            </div>
          </div>

          <v-alert v-if="exportError" type="error" density="compact" class="mt-2">
            {{ exportError }}
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="cancelExport">Cancel</v-btn>
          <v-btn variant="text" :disabled="exporting" @click="runExport('page')">
            This page only ({{ logs.length }})
          </v-btn>
          <v-btn
            color="primary"
            :loading="exporting"
            :disabled="exportTooLarge"
            @click="runExport('all')"
          >
            Export {{ totalLogs.toLocaleString() }} rows
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Copy Snackbar -->
    <v-snackbar v-model="copiedSnackbar" :timeout="2000" color="success">
      Metadata copied to clipboard
    </v-snackbar>

    <v-snackbar v-model="exportedSnackbar" :timeout="3000" color="success">
      Exported {{ exportedRows.toLocaleString() }} rows to CSV
    </v-snackbar>
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

// Column visibility state
const availableMetadataKeys = ref<string[]>([])
const selectedMetadataColumns = ref<string[]>([])

// Standard columns that can be toggled
const standardColumnKeys = ['timestamp', 'level', 'source', 'user_id', 'message'] as const
const visibleStandardColumns = ref<string[]>([...standardColumnKeys])

// LocalStorage key for persisting column preferences
const storageKey = `simplelogs-columns-${teamId}`

// Load saved column preferences from localStorage
function loadColumnPreferences() {
  try {
    const saved = localStorage.getItem(storageKey)
    if (saved) {
      const prefs = JSON.parse(saved)
      if (prefs.metadata) selectedMetadataColumns.value = prefs.metadata
      if (prefs.standard) visibleStandardColumns.value = prefs.standard
    }
  } catch {
    // Ignore parse errors
  }
}

// Save column preferences to localStorage
function saveColumnPreferences() {
  localStorage.setItem(storageKey, JSON.stringify({
    metadata: selectedMetadataColumns.value,
    standard: visibleStandardColumns.value,
  }))
}

// Watch for changes to selected columns and persist
watch([selectedMetadataColumns, visibleStandardColumns], saveColumnPreferences, { deep: true })

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

// Toggle a standard column
function toggleStandardColumn(key: string) {
  const index = visibleStandardColumns.value.indexOf(key)
  if (index === -1) {
    visibleStandardColumns.value.push(key)
  } else {
    visibleStandardColumns.value.splice(index, 1)
  }
}

// Check if a metadata column is selected
function isMetadataColumnSelected(key: string): boolean {
  return selectedMetadataColumns.value.includes(key)
}

// Check if a standard column is visible
function isStandardColumnVisible(key: string): boolean {
  return visibleStandardColumns.value.includes(key)
}

// Select all metadata columns
function selectAllMetadataColumns() {
  selectedMetadataColumns.value = [...availableMetadataKeys.value]
}

// Clear all metadata columns
function clearAllMetadataColumns() {
  selectedMetadataColumns.value = []
}

// Show all standard columns
function showAllStandardColumns() {
  visibleStandardColumns.value = [...standardColumnKeys]
}

// Hide all standard columns
function hideAllStandardColumns() {
  visibleStandardColumns.value = []
}

// Get display value for a metadata field
function getMetadataValue(log: Log, key: string, empty = '-'): string {
  if (!log.metadata || !(key in log.metadata)) {
    return empty
  }
  const value = log.metadata[key]
  if (value === null || value === undefined) {
    return empty
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
  userId: '',
  from: '',
  to: '',
  metadataFilter: '',
})

const levelOptions = ['debug', 'info', 'warn', 'error', 'fatal']

const allStandardHeaders: Record<string, { title: string; key: string; width?: string }> = {
  timestamp: { title: 'Timestamp', key: 'timestamp', width: '180px' },
  level: { title: 'Level', key: 'level', width: '100px' },
  source: { title: 'Source', key: 'source', width: '120px' },
  user_id: { title: 'User ID', key: 'user_id', width: '150px' },
  message: { title: 'Message', key: 'message' },
}

const metadataHeader = { title: 'Metadata', key: 'metadata', width: '130px', sortable: false }

const headers = computed(() => {
  // Filter standard headers based on visibility
  const visibleBaseHeaders = standardColumnKeys
    .filter(key => visibleStandardColumns.value.includes(key))
    .map(key => allStandardHeaders[key])

  // Add selected metadata columns
  const metadataColumns = selectedMetadataColumns.value.map(key => ({
    title: key,
    key: `metadata.${key}`,
    width: '150px',
    sortable: false,
  }))

  return [...visibleBaseHeaders, ...metadataColumns, metadataHeader]
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

// Build the query string for the current filters. `toOverride` pins the upper
// time bound so a multi-page export isn't shifted by logs ingested mid-export.
function buildSearchParams(pageNum: number, limit: number, toOverride?: string): string {
  const params = new URLSearchParams()
  params.append('page', pageNum.toString())
  params.append('limit', limit.toString())

  if (search.q) params.append('q', search.q)
  if (search.source) params.append('source', search.source)
  if (search.userId) params.append('user_id', search.userId)
  if (search.from) params.append('from', new Date(search.from).toISOString())
  const to = search.to ? new Date(search.to).toISOString() : toOverride
  if (to) params.append('to', to)
  search.levels.forEach(level => params.append('level', level))

  // Parse metadata filter
  if (search.metadataFilter) {
    const parts = search.metadataFilter.split('=')
    if (parts.length === 2) {
      params.append(`metadata.${parts[0].trim()}`, parts[1].trim())
    }
  }

  return params.toString()
}

async function fetchLogs() {
  loading.value = true
  try {
    const response = await api.get(
      `/teams/${teamId}/logs?${buildSearchParams(page.value, itemsPerPage.value)}`
    )
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
  search.userId = ''
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

// Value for one exported cell. Missing metadata is left blank rather than the
// table's '-' placeholder.
function cellValue(log: Log, key: string): string {
  if (key === 'timestamp') return formatDate(log.timestamp)
  if (key === 'level') return log.level.toUpperCase()
  if (key === 'source') return log.source || ''
  if (key === 'user_id') return log.user_id || ''
  if (key === 'message') return log.message
  if (key === metadataJsonKey) return log.metadata ? JSON.stringify(log.metadata) : ''
  if (key.startsWith('metadata.')) return getMetadataValue(log, key.substring(9), '')
  return ''
}

// Visible columns minus the "Metadata" column, which is just row actions.
const dataColumns = computed(() => headers.value.filter(h => h.key !== 'metadata'))

const copiedSnackbar = ref(false)

// Copy a single row's metadata to the clipboard as formatted JSON
async function copyMetadata(log: Log) {
  if (!log.metadata) return
  try {
    await navigator.clipboard.writeText(JSON.stringify(log.metadata, null, 2))
    copiedSnackbar.value = true
  } catch (err) {
    console.error('Failed to copy:', err)
  }
}

// ---- CSV export ----

const EXPORT_PAGE_SIZE = 1000 // matches the API's max `limit`
const EXPORT_WARN_ROWS = 10000
const EXPORT_MAX_ROWS = 500000

// Synthetic column key for the full metadata blob (no real header uses it).
const metadataJsonKey = '__metadata_json'

const exportDialog = ref(false)
const exporting = ref(false)
const exportedRows = ref(0)
const exportIncludeMetadata = ref(true)
const exportError = ref('')
const exportedSnackbar = ref(false)
let exportAbort: AbortController | null = null

const exportTooLarge = computed(() => totalLogs.value > EXPORT_MAX_ROWS)
const exportNeedsWarning = computed(() => totalLogs.value > EXPORT_WARN_ROWS)

// Rough size estimate, extrapolated from the rows already on screen.
const estimatedExportBytes = computed(() => {
  if (logs.value.length === 0) return 0
  const cols = exportColumns()
  const sampled = logs.value.reduce((sum, log) => sum + csvRow(log, cols).length + 2, 0)
  return Math.round((sampled / logs.value.length) * totalLogs.value)
})

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`
}

function exportColumns(): { title: string; key: string }[] {
  const cols = dataColumns.value.map(h => ({ title: h.title, key: h.key }))
  if (exportIncludeMetadata.value) cols.push({ title: 'Metadata', key: metadataJsonKey })
  return cols
}

// Quote every field, and neutralise values a spreadsheet would treat as a
// formula. Plain numbers are left alone so they stay numeric.
function csvEscape(value: string): string {
  let v = value ?? ''
  if (/^[=+\-@\t\r]/.test(v) && !/^-?\d+(\.\d+)?$/.test(v)) {
    v = `'${v}`
  }
  return `"${v.replace(/"/g, '""')}"`
}

function csvRow(log: Log, cols: { key: string }[]): string {
  return cols.map(c => csvEscape(cellValue(log, c.key))).join(',')
}

function openExportDialog() {
  exportError.value = ''
  exportedRows.value = 0
  exportDialog.value = true
}

function cancelExport() {
  exportAbort?.abort()
  exportDialog.value = false
}

async function runExport(scope: 'all' | 'page') {
  exporting.value = true
  exportError.value = ''
  exportedRows.value = 0
  exportAbort = new AbortController()

  const cols = exportColumns()
  const rows = [cols.map(c => csvEscape(c.title)).join(',')]

  try {
    if (scope === 'page') {
      logs.value.forEach(log => rows.push(csvRow(log, cols)))
      exportedRows.value = logs.value.length
    } else {
      const target = Math.min(totalLogs.value, EXPORT_MAX_ROWS)
      const pinnedTo = new Date().toISOString()
      let p = 1
      while (exportedRows.value < target) {
        const response = await api.get(
          `/teams/${teamId}/logs?${buildSearchParams(p, EXPORT_PAGE_SIZE, pinnedTo)}`,
          { signal: exportAbort.signal }
        )
        const items: Log[] = response.data.items
        if (items.length === 0) break
        items.forEach(log => rows.push(csvRow(log, cols)))
        exportedRows.value = rows.length - 1
        if (items.length < EXPORT_PAGE_SIZE) break
        p++
      }
    }

    downloadCsv(rows.join('\r\n'))
    exportDialog.value = false
    exportedSnackbar.value = true
  } catch (err: any) {
    if (!exportAbort?.signal.aborted) {
      console.error('Failed to export:', err)
      exportError.value = err.response?.data?.detail || 'Export failed'
    }
  } finally {
    exporting.value = false
    exportAbort = null
  }
}

function downloadCsv(content: string) {
  // BOM so Excel reads it as UTF-8.
  const blob = new Blob(['\uFEFF', content], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')
  link.href = url
  link.download = `${(teamName.value || 'team').replace(/[^\w.-]+/g, '_')}-logs-${stamp}.csv`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

// Backfill state
const backfillDialog = ref(false)
const backfillKey = ref('')
const backfillOverwrite = ref(false)
const backfillLoading = ref(false)
const backfillResult = ref('')
const backfillError = ref(false)

async function runBackfill() {
  backfillLoading.value = true
  backfillResult.value = ''
  backfillError.value = false
  try {
    const response = await api.post(`/teams/${teamId}/logs/backfill-user-id`, {
      metadata_key: backfillKey.value,
      overwrite: backfillOverwrite.value,
    })
    backfillResult.value = response.data.message
    fetchLogs()
  } catch (err: any) {
    backfillError.value = true
    backfillResult.value = err.response?.data?.detail || 'Backfill failed'
  } finally {
    backfillLoading.value = false
  }
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
