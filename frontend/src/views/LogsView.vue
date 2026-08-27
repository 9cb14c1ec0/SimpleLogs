<template>
  <div class="logs-view">
    <!-- Command bar: search and every action in one row -->
    <div class="cmdbar">
      <v-text-field
        v-model="search.q"
        class="cmdbar__search"
        placeholder="Search messages"
        prepend-inner-icon="mdi-magnify"
        variant="solo-filled"
        density="compact"
        flat
        hide-details
        single-line
        clearable
        @keyup.enter="applyFilters"
        @click:clear="applyFilters"
      />

      <v-menu v-model="filterMenuOpen" :close-on-content-click="false" location="bottom end">
        <template #activator="{ props }">
          <v-btn
            v-bind="props"
            variant="text"
            size="small"
            prepend-icon="mdi-filter-variant"
            :active="activeFilters.length > 0"
          >
            Filters
            <!-- Closing the chip clears every filter without opening the menu.
                 VChip stops propagation on close, so it won't trigger the menu. -->
            <v-chip
              v-if="activeFilters.length"
              size="x-small"
              class="ml-2"
              color="primary"
              closable
              close-label="Clear all filters"
              @click:close="resetFilters"
            >
              {{ activeFilters.length }}
            </v-chip>
          </v-btn>
        </template>
        <v-card min-width="340" class="pa-2">
          <v-card-text class="d-flex flex-column ga-3 pb-2">
            <v-select
              v-model="search.levels"
              :items="levelOptions"
              label="Level"
              density="compact"
              variant="outlined"
              hide-details
              multiple
              chips
              closable-chips
            />
            <v-text-field
              v-model="search.source"
              label="Source"
              density="compact"
              variant="outlined"
              hide-details
              clearable
            />
            <v-text-field
              v-model="search.userId"
              label="User ID"
              density="compact"
              variant="outlined"
              hide-details
              clearable
            />
            <div class="d-flex ga-2">
              <v-text-field
                v-model="search.from"
                label="From"
                type="datetime-local"
                density="compact"
                variant="outlined"
                hide-details
              />
              <v-text-field
                v-model="search.to"
                label="To"
                type="datetime-local"
                density="compact"
                variant="outlined"
                hide-details
              />
            </div>
            <v-text-field
              v-model="search.metadataFilter"
              label="Metadata"
              placeholder="user_id=123"
              hint="Format: field=value"
              persistent-hint
              density="compact"
              variant="outlined"
              clearable
              @keyup.enter="applyFilters(); filterMenuOpen = false"
            />
          </v-card-text>
          <v-card-actions>
            <v-btn size="small" variant="text" @click="resetFilters">Clear all</v-btn>
            <v-spacer />
            <v-btn size="small" color="primary" variant="flat" @click="applyFilters(); filterMenuOpen = false">
              Apply
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-menu>

      <v-btn
        variant="text"
        size="small"
        :active="live"
        :title="live ? 'Stop following new logs' : 'Follow new logs as they arrive'"
        @click="toggleLive"
      >
        <span class="livedot" :class="`livedot--${streamStatus}`" />
        Live
      </v-btn>

      <v-btn
        icon="mdi-refresh"
        variant="text"
        size="small"
        title="Refresh"
        :loading="loading"
        @click="refresh"
      />

      <v-spacer />
      <v-divider vertical class="my-2" />

      <v-btn
        variant="text"
        size="small"
        prepend-icon="mdi-chart-bar"
        :to="`/teams/${teamId}/analytics`"
      >
        Analytics
      </v-btn>
      <v-btn
        variant="text"
        size="small"
        prepend-icon="mdi-file-delimited-outline"
        @click="openExportDialog"
        :disabled="logs.length === 0"
      >
        Export
      </v-btn>
      <v-menu location="bottom end">
        <template #activator="{ props }">
          <v-btn v-bind="props" icon="mdi-dots-vertical" variant="text" size="small" />
        </template>
        <v-list density="compact">
          <v-list-item prepend-icon="mdi-database-sync" title="Backfill user ID" @click="backfillDialog = true" />
        </v-list>
      </v-menu>
      <v-menu v-model="columnMenuOpen" :close-on-content-click="false" location="bottom end">
        <template #activator="{ props }">
          <v-btn v-bind="props" variant="text" size="small" prepend-icon="mdi-table-column">
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

    <!-- Active filters, one chip each. Absent entirely when nothing is set. -->
    <div v-if="activeFilters.length" class="filterrail">
      <v-chip
        v-for="f in activeFilters"
        :key="f.id"
        size="small"
        variant="tonal"
        closable
        class="filterrail__chip"
        @click:close="f.clear(); applyFilters()"
      >
        <span class="filterrail__key">{{ f.key }}</span>{{ f.value }}
      </v-chip>
      <v-btn size="x-small" variant="text" class="ml-1" @click="resetFilters">Clear all</v-btn>
    </div>

    <!-- Logs Table -->
    <div ref="tableEl" class="logs-table">
      <!-- Only while the reader has scrolled away from the head -->
      <div v-if="missedWhileScrolled" class="newpill">
        <v-btn size="small" color="primary" variant="flat" prepend-icon="mdi-arrow-up" @click="scrollToLatest">
          {{ missedWhileScrolled.toLocaleString() }} new
        </v-btn>
      </div>

      <v-data-table-server
        v-model:items-per-page="itemsPerPage"
        v-model:page="page"
        :headers="headers"
        :items="logs"
        :items-length="totalLogs"
        :loading="loading"
        :items-per-page-options="[50, 100, 200, 500]"
        density="compact"
        fixed-header
        hover
        @update:options="onTableUpdate"
      >
        <template #item.timestamp="{ item }">
          <span class="nowrap">{{ formatDate(item.timestamp) }}</span>
        </template>
        <template #item.level="{ item }">
          <v-chip :color="getLevelColor(item.level)" size="x-small" label variant="tonal">
            {{ item.level.toUpperCase() }}
          </v-chip>
        </template>
        <template #item.message="{ item }">
          <div class="text-truncate message-cell">
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
    </div>

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
import { onMounted, onUnmounted, ref, reactive, computed, watch, watchEffect, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import api, { type Log } from '@/api/client'
import { pageHeader, resetPageHeader } from '@/composables/usePageHeader'
import { useLogStream } from '@/composables/useLogStream'

const route = useRoute()

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

const filterMenuOpen = ref(false)

// The app bar renders this view's heading
watchEffect(() => {
  pageHeader.title = teamName.value ? `${teamName.value} Logs` : 'Logs'
  pageHeader.meta = `${totalLogs.value.toLocaleString()} entries`
  pageHeader.back = '/'
})
onUnmounted(resetPageHeader)

// Everything set beyond the always-visible search box, as removable chips.
const activeFilters = computed(() => {
  const out: { id: string; key: string; value: string; clear: () => void }[] = []

  search.levels.forEach(level => {
    out.push({
      id: `level:${level}`,
      key: 'level:',
      value: level,
      clear: () => { search.levels = search.levels.filter(l => l !== level) },
    })
  })
  if (search.source) {
    out.push({ id: 'source', key: 'source:', value: search.source, clear: () => { search.source = '' } })
  }
  if (search.userId) {
    out.push({ id: 'user', key: 'user:', value: search.userId, clear: () => { search.userId = '' } })
  }
  if (search.from) {
    out.push({ id: 'from', key: 'from:', value: formatDate(search.from), clear: () => { search.from = '' } })
  }
  if (search.to) {
    out.push({ id: 'to', key: 'to:', value: formatDate(search.to), clear: () => { search.to = '' } })
  }
  if (search.metadataFilter) {
    out.push({
      id: 'meta',
      key: 'meta:',
      value: search.metadataFilter,
      clear: () => { search.metadataFilter = '' },
    })
  }

  return out
})

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
function buildFilterParams(toOverride?: string): URLSearchParams {
  const params = new URLSearchParams()

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

  return params
}

function buildSearchParams(pageNum: number, limit: number, toOverride?: string): string {
  const params = buildFilterParams(toOverride)
  params.append('page', pageNum.toString())
  params.append('limit', limit.toString())
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
  // Paging away from the head and tailing the head are incompatible.
  if (live.value && options.page !== 1) {
    live.value = false
    stopStream()
  }
  page.value = options.page
  itemsPerPage.value = options.itemsPerPage
  fetchLogs()
}

// ---- Live stream ----

// Newest-first, so streamed rows land at the top. Keep the list bounded or a
// busy team grows it without limit.
const MAX_LIVE_ROWS = 500
// Treat "within a row height of the top" as still following the head.
const FOLLOW_THRESHOLD_PX = 40

const live = ref(false)
const missedWhileScrolled = ref(0)
const tableEl = ref<HTMLElement | null>(null)

function scroller(): HTMLElement | null {
  return tableEl.value?.querySelector('.v-table__wrapper') ?? null
}

const { status: streamStatus, start: startStream, stop: stopStream } = useLogStream({
  url: () => {
    const params = buildFilterParams()
    const newest = logs.value[0]?.id
    if (newest !== undefined) params.append('after_id', String(newest))
    return `/api/v1/teams/${teamId}/logs/stream?${params.toString()}`
  },
  onBatch: onStreamedLogs,
})

function onStreamedLogs(incoming: Log[]) {
  // A reconnect resumes from the newest row held, but a refetch racing the
  // stream can still deliver rows twice. Merging by id keeps that harmless.
  const known = new Set(logs.value.map(log => log.id))
  const fresh = incoming.filter(log => !known.has(log.id))
  if (fresh.length === 0) return

  const el = scroller()
  const following = !el || el.scrollTop <= FOLLOW_THRESHOLD_PX
  const heightBefore = el?.scrollHeight ?? 0

  // The stream sends oldest-first; the table reads newest-first.
  logs.value = [...fresh.slice().reverse(), ...logs.value].slice(0, MAX_LIVE_ROWS)
  totalLogs.value += fresh.length

  const keys = new Set([...availableMetadataKeys.value, ...extractMetadataKeys(fresh)])
  availableMetadataKeys.value = Array.from(keys).sort()

  if (!el) return
  if (following) {
    // Already at the head, so nothing is unseen.
    missedWhileScrolled.value = 0
    nextTick(() => { el.scrollTop = 0 })
  } else {
    // Hold the reader's place: new rows above them would otherwise push the
    // row they were looking at down the screen.
    missedWhileScrolled.value += fresh.length
    nextTick(() => { el.scrollTop += el.scrollHeight - heightBefore })
  }
}

// Refetching while the stream is open would re-deliver everything ingested
// since the connection opened, so restart it on the new cursor. Unlike
// applyFilters this keeps the current page, which is what refresh means.
function refresh() {
  const loaded = fetchLogs()
  if (!live.value) return
  stopStream()
  loaded.then(() => { if (live.value) startStream() })
}

function scrollToLatest() {
  missedWhileScrolled.value = 0
  const el = scroller()
  if (el) el.scrollTo({ top: 0, behavior: 'smooth' })
}

function toggleLive() {
  live.value = !live.value
  if (live.value) {
    page.value = 1
    missedWhileScrolled.value = 0
    // Refetch first so the stream resumes from a known-current cursor.
    fetchLogs().then(() => { if (live.value) startStream() })
  } else {
    stopStream()
    missedWhileScrolled.value = 0
  }
}

// Any filter change starts a fresh result set, so page 7 of the old one is
// never carried over.
function applyFilters() {
  page.value = 1
  missedWhileScrolled.value = 0
  const loaded = fetchLogs()
  if (live.value) {
    // The stream filters server-side, so it has to be rebuilt to match.
    stopStream()
    loaded.then(() => { if (live.value) startStream() })
  }
}

onUnmounted(() => stopStream())

function resetFilters() {
  search.q = ''
  search.levels = []
  search.source = ''
  search.userId = ''
  search.from = ''
  search.to = ''
  search.metadataFilter = ''
  applyFilters()
}

// Fixed-width, sortable-looking, and one line at any zoom: 2026-08-27 10:00:00
function formatDate(date: string) {
  const d = new Date(date)
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ` +
    `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  )
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

/* Chrome is sans and quiet; log data is mono so columns of ids, timestamps
   and levels line up vertically for scanning. */
.logs-view {
  --data-font: ui-monospace, 'Cascadia Mono', 'SF Mono', Menlo, Consolas, monospace;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.cmdbar {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 0 0 auto;
  height: 52px;
  padding: 0 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.09);
}

.cmdbar__search {
  max-width: 420px;
  flex: 0 1 420px;
  margin-right: 4px;
}

.filterrail {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  flex: 0 0 auto;
  padding: 6px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.09);
}

.filterrail__chip {
  font-family: var(--data-font);
  font-size: 11px;
}

.filterrail__key {
  opacity: 0.55;
  margin-right: 2px;
}

.livedot {
  width: 7px;
  height: 7px;
  margin-right: 7px;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.35;
}

.livedot--connecting {
  background: rgb(var(--v-theme-warning));
  opacity: 1;
}

.livedot--error {
  background: rgb(var(--v-theme-error));
  opacity: 1;
}

.livedot--live {
  background: rgb(var(--v-theme-success));
  opacity: 1;
  animation: livepulse 2s ease-in-out infinite;
}

@keyframes livepulse {
  50% { opacity: 0.3; }
}

@media (prefers-reduced-motion: reduce) {
  .livedot--live {
    animation: none;
  }
}

/* The table owns all leftover height; only its body scrolls. */
.logs-table {
  position: relative;
  flex: 1 1 0;
  min-height: 0;
}

.newpill {
  position: absolute;
  top: 48px;
  left: 50%;
  z-index: 3;
  transform: translateX(-50%);
}

.logs-table :deep(.v-table) {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: transparent;
}

.logs-table :deep(.v-table__wrapper) {
  flex: 1 1 auto;
  min-height: 0;
}

.logs-table :deep(thead th) {
  font-size: 10px !important;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.6;
  white-space: nowrap;
}

.logs-table :deep(tbody td) {
  font-family: var(--data-font);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.nowrap {
  white-space: nowrap;
}

/* A log line can be tens of thousands of characters; without a hard cap the
   cell sizes the whole table to its content. */
.message-cell {
  max-width: 720px;
}

.metadata-cell {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
