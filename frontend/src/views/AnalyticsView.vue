<template>
  <div>
    <!-- Header -->
    <div class="d-flex align-center mb-4">
      <v-btn icon variant="text" @click="router.push('/')">
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
      <h1 class="text-h4 ml-2">{{ teamName }} Analytics</h1>
      <v-spacer />
      <v-menu :close-on-content-click="false">
        <template #activator="{ props }">
          <v-btn variant="tonal" prepend-icon="mdi-chart-bar" v-bind="props" class="mr-2">
            Charts
          </v-btn>
        </template>
        <v-list density="compact">
          <v-list-item v-for="c in ALL_CHARTS" :key="c.id" @click="toggleChart(c.id)">
            <template #prepend>
              <v-checkbox-btn :model-value="!hiddenCharts.has(c.id)" readonly />
            </template>
            <v-list-item-title>{{ c.label }}</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
      <v-btn
        variant="tonal"
        prepend-icon="mdi-text-box-outline"
        :to="`/teams/${teamId}/logs`"
      >
        View Logs
      </v-btn>
    </div>

    <!-- Time Range Picker -->
    <div class="mb-6">
      <TimeRangePicker ref="picker" @change="onRangeChange" />
    </div>

    <v-progress-linear v-if="loading" indeterminate class="mb-4" />

    <!-- Row 1: Volume + Donut -->
    <v-row class="mb-4">
      <v-col v-if="!hiddenCharts.has('volume')" cols="12" md="8">
        <v-card>
          <v-card-title class="d-flex align-center text-subtitle-1">
            Log Volume Over Time
            <v-spacer />
            <v-btn icon variant="text" size="x-small" @click="hideChart('volume')"><v-icon>mdi-close</v-icon></v-btn>
          </v-card-title>
          <v-card-text>
            <VChart v-if="volumeChartOption" :option="volumeChartOption" autoresize style="height: 300px" />
            <div v-else class="text-center text-grey py-12">No data for this time range</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col v-if="!hiddenCharts.has('levelDonut')" cols="12" md="4">
        <v-card>
          <v-card-title class="d-flex align-center text-subtitle-1">
            Level Breakdown
            <v-spacer />
            <v-btn icon variant="text" size="x-small" @click="hideChart('levelDonut')"><v-icon>mdi-close</v-icon></v-btn>
          </v-card-title>
          <v-card-text>
            <VChart v-if="levelDonutOption" :option="levelDonutOption" autoresize style="height: 300px" />
            <div v-else class="text-center text-grey py-12">No data</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Row 2: Error Rate + Top Sources -->
    <v-row class="mb-4">
      <v-col v-if="!hiddenCharts.has('errorRate')" cols="12" md="6">
        <v-card>
          <v-card-title class="d-flex align-center text-subtitle-1">
            Error Rate Over Time
            <v-spacer />
            <v-btn icon variant="text" size="x-small" @click="hideChart('errorRate')"><v-icon>mdi-close</v-icon></v-btn>
          </v-card-title>
          <v-card-text>
            <VChart v-if="errorRateChartOption" :option="errorRateChartOption" autoresize style="height: 300px" />
            <div v-else class="text-center text-grey py-12">No data</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col v-if="!hiddenCharts.has('topSources')" cols="12" md="6">
        <v-card>
          <v-card-title class="d-flex align-center text-subtitle-1">
            Top Sources
            <v-spacer />
            <v-btn icon variant="text" size="x-small" @click="hideChart('topSources')"><v-icon>mdi-close</v-icon></v-btn>
          </v-card-title>
          <v-card-text>
            <VChart v-if="topSourcesOption" :option="topSourcesOption" autoresize style="height: 300px" />
            <div v-else class="text-center text-grey py-12">No data</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Row 3: Top Errors Table + Top Users -->
    <v-row class="mb-4">
      <v-col v-if="!hiddenCharts.has('topErrors')" cols="12" md="6">
        <v-card>
          <v-card-title class="d-flex align-center text-subtitle-1">
            Top Error Messages
            <v-spacer />
            <v-btn icon variant="text" size="x-small" @click="hideChart('topErrors')"><v-icon>mdi-close</v-icon></v-btn>
          </v-card-title>
          <v-card-text>
            <v-table v-if="topErrorsData.length > 0" density="compact">
              <thead>
                <tr>
                  <th>Message</th>
                  <th class="text-right" style="width: 100px">Count</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, i) in topErrorsData" :key="i">
                  <td class="text-truncate" style="max-width: 400px">{{ item.value }}</td>
                  <td class="text-right">{{ item.count.toLocaleString() }}</td>
                </tr>
              </tbody>
            </v-table>
            <div v-else class="text-center text-grey py-12">No errors in this time range</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col v-if="!hiddenCharts.has('topUsers')" cols="12" md="6">
        <v-card>
          <v-card-title class="d-flex align-center text-subtitle-1">
            Logs per User
            <v-spacer />
            <v-btn icon variant="text" size="x-small" @click="hideChart('topUsers')"><v-icon>mdi-close</v-icon></v-btn>
          </v-card-title>
          <v-card-text>
            <VChart v-if="topUsersOption" :option="topUsersOption" autoresize style="height: 300px" />
            <div v-else class="text-center text-grey py-12">No user data</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Row 4: Top Users Volume Over Time -->
    <v-row v-if="!hiddenCharts.has('topUsersVolume')" class="mb-4">
      <v-col cols="12">
        <v-card>
          <v-card-title class="d-flex align-center text-subtitle-1">
            Top Users Volume Over Time
            <v-spacer />
            <v-btn icon variant="text" size="x-small" @click="hideChart('topUsersVolume')"><v-icon>mdi-close</v-icon></v-btn>
          </v-card-title>
          <v-card-text>
            <VChart v-if="topUsersVolumeOption" :option="topUsersVolumeOption" autoresize style="height: 300px" />
            <div v-else class="text-center text-grey py-12">No user data</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Row 5: Heatmap -->
    <v-row v-if="!hiddenCharts.has('heatmap')" class="mb-4">
      <v-col cols="12">
        <v-card>
          <v-card-title class="d-flex align-center text-subtitle-1">
            Source x Level Heatmap
            <v-spacer />
            <v-btn icon variant="text" size="x-small" @click="hideChart('heatmap')"><v-icon>mdi-close</v-icon></v-btn>
          </v-card-title>
          <v-card-text>
            <VChart v-if="heatmapOption" :option="heatmapOption" autoresize :style="{ height: heatmapHeight }" />
            <div v-else class="text-center text-grey py-12">No data</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/client'
import { VChart } from '@/plugins/echarts'
import TimeRangePicker from '@/components/TimeRangePicker.vue'
import { useAnalytics, type TimeRange } from '@/composables/useAnalytics'
import { useChartOptions } from '@/composables/useChartOptions'

const route = useRoute()
const router = useRouter()

const teamId = route.params.teamId as string
const teamName = ref('')
const picker = ref<InstanceType<typeof TimeRangePicker> | null>(null)

// -- Closable charts --
const ALL_CHARTS = [
  { id: 'volume', label: 'Log Volume Over Time' },
  { id: 'levelDonut', label: 'Level Breakdown' },
  { id: 'errorRate', label: 'Error Rate Over Time' },
  { id: 'topSources', label: 'Top Sources' },
  { id: 'topErrors', label: 'Top Error Messages' },
  { id: 'topUsers', label: 'Logs per User' },
  { id: 'topUsersVolume', label: 'Top Users Volume Over Time' },
  { id: 'heatmap', label: 'Source x Level Heatmap' },
] as const

type ChartId = typeof ALL_CHARTS[number]['id']

const storageKey = `simplelogs-hidden-charts-${teamId}`

function loadHidden(): Set<ChartId> {
  try {
    const raw = localStorage.getItem(storageKey)
    if (raw) return new Set(JSON.parse(raw) as ChartId[])
  } catch { /* ignore */ }
  return new Set()
}

const hiddenCharts = reactive(loadHidden())

watch(() => [...hiddenCharts], (ids) => {
  localStorage.setItem(storageKey, JSON.stringify(ids))
})

function hideChart(id: ChartId) {
  hiddenCharts.add(id)
}

function toggleChart(id: ChartId) {
  if (hiddenCharts.has(id)) {
    hiddenCharts.delete(id)
  } else {
    hiddenCharts.add(id)
  }
}

// -- Analytics data --
const {
  volume,
  topSources,
  topErrors,
  topUsers,
  topUsersVolume,
  heatmap,
  loading,
  fetchAll,
} = useAnalytics(teamId)

const {
  volumeChartOption,
  errorRateChartOption,
  levelDonutOption,
  topSourcesOption,
  topErrorsData,
  topUsersOption,
  topUsersVolumeOption,
  heatmapOption,
} = useChartOptions(volume, topSources, topErrors, topUsers, topUsersVolume, heatmap)

const heatmapHeight = computed(() => {
  const sources = heatmap.value?.sources.length ?? 0
  return `${Math.max(200, sources * 30 + 80)}px`
})

function onRangeChange(range: TimeRange, bucket: string) {
  fetchAll(range, bucket)
}

onMounted(async () => {
  try {
    const response = await api.get(`/admin/teams/${teamId}`)
    teamName.value = response.data.name
  } catch {
    teamName.value = 'Unknown Team'
  }
  picker.value?.emitInitial()
})
</script>
