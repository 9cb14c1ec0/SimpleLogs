import { computed, type Ref } from 'vue'
import type {
  VolumeResponse,
  TopResponse,
  HeatmapResponse,
} from '@/api/client'

const LEVEL_COLORS: Record<string, string> = {
  debug: '#9e9e9e',
  info: '#42a5f5',
  warn: '#ffa726',
  error: '#ef5350',
  fatal: '#ab47bc',
}

const ALL_LEVELS = ['debug', 'info', 'warn', 'error', 'fatal']

function formatBucket(iso: string): string {
  const d = new Date(iso)
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hour = String(d.getHours()).padStart(2, '0')
  return `${month}/${day} ${hour}:00`
}

export function useChartOptions(
  volume: Ref<VolumeResponse | null>,
  topSources: Ref<TopResponse | null>,
  topErrors: Ref<TopResponse | null>,
  topUsers: Ref<TopResponse | null>,
  heatmap: Ref<HeatmapResponse | null>,
) {

  // Chart 1: Log volume over time (stacked bar by level)
  const volumeChartOption = computed(() => {
    const data = volume.value
    if (!data || data.buckets.length === 0) return null

    // Get unique sorted buckets
    const bucketSet = [...new Set(data.buckets.map(b => b.bucket))].sort()
    const xLabels = bucketSet.map(formatBucket)

    // Group by level
    const series = ALL_LEVELS.map(level => {
      const counts = bucketSet.map(bucket => {
        const entry = data.buckets.find(b => b.bucket === bucket && b.level === level)
        return entry?.count ?? 0
      })
      return {
        name: level,
        type: 'bar' as const,
        stack: 'total',
        data: counts,
        itemStyle: { color: LEVEL_COLORS[level] },
      }
    })

    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ALL_LEVELS, top: 0 },
      grid: { left: 50, right: 20, bottom: 40, top: 40 },
      xAxis: { type: 'category', data: xLabels },
      yAxis: { type: 'value' },
      series,
    }
  })

  // Chart 2: Error rate over time (area line %)
  const errorRateChartOption = computed(() => {
    const data = volume.value
    if (!data || data.buckets.length === 0) return null

    const bucketSet = [...new Set(data.buckets.map(b => b.bucket))].sort()
    const xLabels = bucketSet.map(formatBucket)

    const rates = bucketSet.map(bucket => {
      const entries = data.buckets.filter(b => b.bucket === bucket)
      const total = entries.reduce((s, e) => s + e.count, 0)
      if (total === 0) return 0
      const errors = entries
        .filter(e => e.level === 'error' || e.level === 'fatal')
        .reduce((s, e) => s + e.count, 0)
      return +((errors / total) * 100).toFixed(2)
    })

    return {
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          const p = Array.isArray(params) ? params[0] : params
          return `${p.name}<br/>Error rate: ${p.value}%`
        },
      },
      grid: { left: 50, right: 20, bottom: 40, top: 20 },
      xAxis: { type: 'category', data: xLabels },
      yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
      series: [{
        name: 'Error Rate',
        type: 'line',
        areaStyle: { opacity: 0.3 },
        data: rates,
        itemStyle: { color: '#ef5350' },
      }],
    }
  })

  // Chart 3: Level breakdown donut
  const levelDonutOption = computed(() => {
    const data = volume.value
    if (!data) return null

    const total = Object.values(data.totals).reduce((a, b) => a + b, 0)
    if (total === 0) return null

    const seriesData = ALL_LEVELS
      .filter(level => (data.totals[level] ?? 0) > 0)
      .map(level => ({
        name: level,
        value: data.totals[level] ?? 0,
        itemStyle: { color: LEVEL_COLORS[level] },
      }))

    return {
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)',
      },
      legend: { orient: 'vertical', left: 0, top: 'center' },
      series: [{
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['60%', '50%'],
        avoidLabelOverlap: true,
        label: { show: false },
        data: seriesData,
      }],
    }
  })

  // Chart 4: Top sources horizontal bar
  const topSourcesOption = computed(() => {
    const data = topSources.value
    if (!data || data.items.length === 0) return null

    const items = [...data.items].reverse()

    return {
      tooltip: { trigger: 'axis' },
      grid: { left: 120, right: 30, bottom: 20, top: 10 },
      xAxis: { type: 'value' },
      yAxis: { type: 'category', data: items.map(i => i.value) },
      series: [{
        type: 'bar',
        data: items.map(i => i.count),
        itemStyle: { color: '#42a5f5' },
      }],
    }
  })

  // Chart 5: Top error messages (table - rendered as horizontal bar for consistency)
  const topErrorsData = computed(() => {
    return topErrors.value?.items ?? []
  })

  // Chart 6: Logs per user_id horizontal bar
  const topUsersOption = computed(() => {
    const data = topUsers.value
    if (!data || data.items.length === 0) return null

    const items = [...data.items].reverse()

    return {
      tooltip: { trigger: 'axis' },
      grid: { left: 120, right: 30, bottom: 20, top: 10 },
      xAxis: { type: 'value' },
      yAxis: { type: 'category', data: items.map(i => i.value) },
      series: [{
        type: 'bar',
        data: items.map(i => i.count),
        itemStyle: { color: '#66bb6a' },
      }],
    }
  })

  // Chart 7: Source x Level heatmap
  const heatmapOption = computed(() => {
    const data = heatmap.value
    if (!data || data.data.length === 0) return null

    const sources = data.sources
    const levels = data.levels

    // Build 2D data: [levelIndex, sourceIndex, count]
    const heatData: [number, number, number][] = []
    let maxCount = 0
    for (const cell of data.data) {
      const si = sources.indexOf(cell.source)
      const li = levels.indexOf(cell.level)
      if (si >= 0 && li >= 0) {
        heatData.push([li, si, cell.count])
        if (cell.count > maxCount) maxCount = cell.count
      }
    }

    return {
      tooltip: {
        formatter: (params: any) => {
          const d = params.data
          return `${sources[d[1]]} / ${levels[d[0]]}: ${d[2]}`
        },
      },
      grid: { left: 120, right: 60, bottom: 40, top: 10 },
      xAxis: { type: 'category', data: levels, splitArea: { show: true } },
      yAxis: { type: 'category', data: sources, splitArea: { show: true } },
      visualMap: {
        min: 0,
        max: maxCount || 1,
        calculable: true,
        orient: 'vertical',
        right: 0,
        top: 'center',
        inRange: { color: ['#1a1a2e', '#ef5350'] },
      },
      series: [{
        type: 'heatmap',
        data: heatData,
        label: { show: true },
      }],
    }
  })

  return {
    volumeChartOption,
    errorRateChartOption,
    levelDonutOption,
    topSourcesOption,
    topErrorsData,
    topUsersOption,
    heatmapOption,
  }
}
