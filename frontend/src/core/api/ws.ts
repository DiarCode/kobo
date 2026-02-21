import { API_BASE_URL } from '@/core/api/http'

function resolveDefaultWsBaseUrl() {
  const apiDerived = API_BASE_URL.replace(/^http/i, 'ws').replace(/\/api\/v1\/?$/i, '')
  if (apiDerived.length > 0) {
    return apiDerived
  }
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    return `${protocol}://${window.location.host}`
  }
  return 'ws://localhost:8000'
}

export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL ?? resolveDefaultWsBaseUrl()

export function openWorkspaceSocket(workspaceId: string, onMessage: (data: unknown) => void): WebSocket {
  const ws = new WebSocket(`${WS_BASE_URL}/ws/workspaces/${workspaceId}/events`)
  ws.onmessage = (event) => {
    try {
      onMessage(JSON.parse(event.data) as unknown)
    } catch {
      onMessage(event.data)
    }
  }
  return ws
}

export function openWorkspacePresenceSocket(workspaceId: string, onMessage: (data: unknown) => void): WebSocket {
  const ws = new WebSocket(`${WS_BASE_URL}/ws/workspaces/${workspaceId}/presence`)
  ws.onmessage = (event) => {
    try {
      onMessage(JSON.parse(event.data) as unknown)
    } catch {
      onMessage(event.data)
    }
  }
  return ws
}
