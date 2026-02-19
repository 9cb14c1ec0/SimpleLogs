<template>
  <div class="d-flex align-center ga-2 flex-wrap">
    <v-btn-toggle v-model="selected" mandatory density="compact" color="primary">
      <v-btn value="24h">24h</v-btn>
      <v-btn value="7d">7d</v-btn>
      <v-btn value="30d">30d</v-btn>
      <v-btn value="custom">Custom</v-btn>
    </v-btn-toggle>

    <template v-if="selected === 'custom'">
      <v-text-field
        v-model="customFrom"
        type="datetime-local"
        label="From"
        density="compact"
        hide-details
        style="max-width: 220px"
        @change="emitCustom"
      />
      <v-text-field
        v-model="customTo"
        type="datetime-local"
        label="To"
        density="compact"
        hide-details
        style="max-width: 220px"
        @change="emitCustom"
      />
      <v-btn size="small" color="primary" variant="tonal" @click="emitCustom">Apply</v-btn>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

export interface TimeRange {
  from: string
  to: string
}

const emit = defineEmits<{
  change: [range: TimeRange, bucket: string]
}>()

const selected = ref('24h')
const customFrom = ref('')
const customTo = ref('')

function presetRange(preset: string): { range: TimeRange; bucket: string } {
  const now = new Date()
  const to = now.toISOString()
  let from: string
  let bucket: string

  switch (preset) {
    case '7d':
      from = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString()
      bucket = 'day'
      break
    case '30d':
      from = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString()
      bucket = 'week'
      break
    default: // 24h
      from = new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString()
      bucket = 'hour'
  }

  return { range: { from, to }, bucket }
}

watch(selected, (val) => {
  if (val !== 'custom') {
    const { range, bucket } = presetRange(val)
    emit('change', range, bucket)
  }
})

function emitCustom() {
  if (customFrom.value && customTo.value) {
    const from = new Date(customFrom.value).toISOString()
    const to = new Date(customTo.value).toISOString()
    const diffMs = new Date(to).getTime() - new Date(from).getTime()
    const diffDays = diffMs / (1000 * 60 * 60 * 24)
    const bucket = diffDays <= 2 ? 'hour' : diffDays <= 14 ? 'day' : 'week'
    emit('change', { from, to }, bucket)
  }
}

// Emit initial range
function emitInitial() {
  const { range, bucket } = presetRange('24h')
  emit('change', range, bucket)
}

defineExpose({ emitInitial })
</script>
