import { apiRequest } from '../api/client'
import type { ResearchEvent } from '../types'

const WS_URL = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000/api/v1/ws'

export function connectResearchSocket(
  jobId: string,
  token: string,
  onEvent: (event: ResearchEvent) => void,
  onState?: (state: 'open' | 'closed' | 'error') => void,
): () => void {
  let stopped = false
  let socket: WebSocket | null = null
  let retryTimer: number | undefined
  let retryCount = 0

  const connect = async () => {
    if (stopped) return
    try {
      const { ticket } = await apiRequest<{ ticket: string }>('/auth/ws-ticket', { method: 'POST' }, token)
      if (stopped) return
      socket = new WebSocket(`${WS_URL}/research/${jobId}?ticket=${encodeURIComponent(ticket)}`)
      socket.onopen = () => {
        retryCount = 0
        onState?.('open')
      }
      socket.onmessage = (message) => {
        try {
          onEvent(JSON.parse(message.data as string) as ResearchEvent)
        } catch {
          // Ignore malformed events; persisted events can be recovered through REST.
        }
      }
      socket.onerror = () => onState?.('error')
      socket.onclose = () => {
        onState?.('closed')
        scheduleReconnect()
      }
    } catch {
      onState?.('error')
      scheduleReconnect()
    }
  }

  const scheduleReconnect = () => {
    if (stopped || retryCount >= 6) return
    retryCount += 1
    retryTimer = window.setTimeout(() => void connect(), Math.min(1000 * 2 ** retryCount, 15000))
  }

  void connect()
  return () => {
    stopped = true
    if (retryTimer) window.clearTimeout(retryTimer)
    socket?.close()
  }
}
