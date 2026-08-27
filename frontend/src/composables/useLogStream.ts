import { ref } from 'vue'
import { refreshAccessToken, type Log } from '@/api/client'

export type StreamStatus = 'off' | 'connecting' | 'live' | 'error'

const FLUSH_MS = 120
const MAX_BACKOFF_MS = 15000

/**
 * Consumes the SSE log stream.
 *
 * Uses fetch rather than EventSource so the request can carry the bearer token
 * and refresh it on expiry; EventSource cannot set headers.
 */
export function useLogStream(options: {
  /** Built fresh per connection attempt so reconnects resume from the newest row. */
  url: () => string
  onBatch: (logs: Log[]) => void
}) {
  const status = ref<StreamStatus>('off')

  let controller: AbortController | null = null
  let stopped = true
  let attempt = 0
  let pending: Log[] = []
  let flushTimer: ReturnType<typeof setTimeout> | null = null

  function flush() {
    flushTimer = null
    if (pending.length === 0) return
    const batch = pending
    pending = []
    options.onBatch(batch)
  }

  // A burst of ingests arrives as one event per log; batch them so the table
  // re-renders once rather than once per row.
  function queue(log: Log) {
    pending.push(log)
    if (flushTimer === null) flushTimer = setTimeout(flush, FLUSH_MS)
  }

  function handleFrame(frame: string) {
    let name = 'message'
    const data: string[] = []

    for (const line of frame.split('\n')) {
      if (line.startsWith(':')) continue // heartbeat
      if (line.startsWith('event:')) name = line.slice(6).trim()
      else if (line.startsWith('data:')) data.push(line.slice(5).trim())
    }

    if (name !== 'log' || data.length === 0) return
    try {
      queue(JSON.parse(data.join('\n')) as Log)
    } catch {
      // Ignore a malformed frame rather than tearing down the stream
    }
  }

  async function consume(body: ReadableStream<Uint8Array>) {
    const reader = body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    for (;;) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      let split = buffer.indexOf('\n\n')
      while (split !== -1) {
        handleFrame(buffer.slice(0, split))
        buffer = buffer.slice(split + 2)
        split = buffer.indexOf('\n\n')
      }
    }
  }

  function headers(): HeadersInit {
    return {
      Authorization: `Bearer ${localStorage.getItem('access_token') ?? ''}`,
      Accept: 'text/event-stream',
    }
  }

  async function connect() {
    if (stopped) return
    controller = new AbortController()
    if (status.value !== 'live') status.value = 'connecting'

    try {
      let response = await fetch(options.url(), { headers: headers(), signal: controller.signal })

      // The access token outlives most connections but not all of them.
      if (response.status === 401) {
        await refreshAccessToken()
        response = await fetch(options.url(), { headers: headers(), signal: controller.signal })
      }

      // Not transient: the user can't read this team, or the backend predates
      // the stream endpoint (older builds route /stream into the by-id lookup
      // and reject it as a bad log id).
      if (response.status === 403 || response.status === 404 || response.status === 422) {
        console.error(`Log stream unavailable (${response.status})`)
        stopped = true
        status.value = 'error'
        return
      }

      if (!response.ok || !response.body) throw new Error(`stream responded ${response.status}`)

      status.value = 'live'
      attempt = 0
      await consume(response.body)
    } catch (err) {
      if (stopped || (err as Error)?.name === 'AbortError') return
      console.error('Log stream dropped:', err)
      status.value = 'error'
    }

    // A clean end-of-body is still a disconnect, so reconnect either way.
    if (stopped) return
    attempt += 1
    setTimeout(connect, Math.min(MAX_BACKOFF_MS, 1000 * 2 ** (attempt - 1)))
  }

  function start() {
    if (!stopped) return
    stopped = false
    attempt = 0
    connect()
  }

  function stop() {
    stopped = true
    controller?.abort()
    controller = null
    if (flushTimer !== null) {
      clearTimeout(flushTimer)
      flushTimer = null
    }
    pending = []
    status.value = 'off'
  }

  return { status, start, stop }
}
