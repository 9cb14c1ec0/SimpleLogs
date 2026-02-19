import { ref, type Ref } from 'vue'
import api, {
  type VolumeResponse,
  type TopResponse,
  type HeatmapResponse,
} from '@/api/client'

export interface TimeRange {
  from: string   // ISO string
  to: string     // ISO string
}

export function useAnalytics(teamId: string) {
  const volume = ref<VolumeResponse | null>(null) as Ref<VolumeResponse | null>
  const topSources = ref<TopResponse | null>(null) as Ref<TopResponse | null>
  const topErrors = ref<TopResponse | null>(null) as Ref<TopResponse | null>
  const topUsers = ref<TopResponse | null>(null) as Ref<TopResponse | null>
  const heatmap = ref<HeatmapResponse | null>(null) as Ref<HeatmapResponse | null>
  const loading = ref(false)

  function rangeParams(range: TimeRange) {
    return { from: range.from, to: range.to }
  }

  async function fetchAll(range: TimeRange, bucket: string) {
    loading.value = true
    try {
      const params = rangeParams(range)
      const [volRes, srcRes, errRes, usrRes, hmRes] = await Promise.all([
        api.get(`/teams/${teamId}/analytics/volume`, {
          params: { ...params, bucket, split_by: 'level' },
        }),
        api.get(`/teams/${teamId}/analytics/top`, {
          params: { ...params, field: 'source' },
        }),
        api.get(`/teams/${teamId}/analytics/top`, {
          params: { ...params, field: 'message', level: ['error', 'fatal'] },
        }),
        api.get(`/teams/${teamId}/analytics/top`, {
          params: { ...params, field: 'user_id' },
        }),
        api.get(`/teams/${teamId}/analytics/heatmap`, {
          params,
        }),
      ])
      volume.value = volRes.data
      topSources.value = srcRes.data
      topErrors.value = errRes.data
      topUsers.value = usrRes.data
      heatmap.value = hmRes.data
    } catch (e) {
      console.error('Failed to fetch analytics:', e)
    } finally {
      loading.value = false
    }
  }

  return {
    volume,
    topSources,
    topErrors,
    topUsers,
    heatmap,
    loading,
    fetchAll,
  }
}
