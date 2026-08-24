import { create } from 'zustand'
import type { SimEvent } from './types'

export interface Notification {
  id: string
  level: 'critical' | 'warning' | 'info'
  title: string
  detail: string
  day: number
  event: SimEvent
  read: boolean
  createdAt: number
}

interface NotificationState {
  notifications: Notification[]
  toasts: Notification[]
  seenEventIds: Set<string>
  push: (n: Notification) => void
  dismissToast: (id: string) => void
  markAllRead: () => void
  markRead: (id: string) => void
  clear: () => void
}

export const useNotificationStore = create<NotificationState>((set) => ({
  notifications: [],
  toasts: [],
  seenEventIds: new Set(),
  push: (n) =>
    set((state) => {
      if (state.seenEventIds.has(n.event.event_id)) return state
      const seen = new Set(state.seenEventIds)
      seen.add(n.event.event_id)
      return {
        seenEventIds: seen,
        notifications: [n, ...state.notifications].slice(0, 100),
        toasts: [...state.toasts, n].slice(-4),
      }
    }),
  dismissToast: (id) => set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
  markAllRead: () => set((state) => ({ notifications: state.notifications.map((n) => ({ ...n, read: true })) })),
  markRead: (id) => set((state) => ({ notifications: state.notifications.map((n) => (n.id === id ? { ...n, read: true } : n)) })),
  clear: () => set({ notifications: [] }),
}))

// Which event types are notification-worthy, and how to describe them --
// derived from real payload data, never invented.
const SIGNIFICANCE: Record<string, { level: Notification['level']; title: (e: SimEvent) => string }> = {
  DISASTER_STARTED: { level: 'critical', title: (e) => `Disaster: ${String(e.payload.disaster_type ?? '').replace(/_/g, ' ')} began` },
  DISASTER_ENDED: { level: 'info', title: (e) => `Disaster: ${String(e.payload.disaster_type ?? '').replace(/_/g, ' ')} ended` },
  BUSINESS_FAILED: { level: 'warning', title: () => 'Business failed' },
  CITIZEN_DIED: { level: 'warning', title: () => 'A citizen has died' },
  AI_DECISION_PROPOSED: { level: 'info', title: () => 'AI proposal awaiting validation' },
  AI_DECISION_REJECTED: { level: 'warning', title: () => 'AI proposal rejected by validator' },
}

export function notificationFromEvent(e: SimEvent): Notification | null {
  const rule = SIGNIFICANCE[e.event_type]
  if (!rule) return null
  return {
    id: e.event_id,
    level: rule.level,
    title: rule.title(e),
    detail: `${e.source_entity} — day ${Math.floor(e.simulation_tick / 24)}`,
    day: Math.floor(e.simulation_tick / 24),
    event: e,
    read: false,
    createdAt: Date.now(),
  }
}
