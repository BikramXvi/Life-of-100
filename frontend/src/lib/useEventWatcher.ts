import { useEffect, useRef } from 'react'
import { useEvents } from './hooks'
import { notificationFromEvent, useNotificationStore } from './notifications'

/** Watches the live event feed and pushes newly-seen, notification-worthy
 * events into the global store. Mounted once at the app shell level. */
export function useEventWatcher() {
  const { data: events } = useEvents(100)
  const push = useNotificationStore((s) => s.push)
  const initialized = useRef(false)

  useEffect(() => {
    if (!events) return
    // On first load, mark everything as already-seen (don't toast a flood
    // of history the moment the app opens) -- only genuinely new events
    // from here on trigger a notification.
    if (!initialized.current) {
      initialized.current = true
      const seen = useNotificationStore.getState().seenEventIds
      for (const e of events) seen.add(e.event_id)
      return
    }
    for (const e of events) {
      const n = notificationFromEvent(e)
      if (n) push(n)
    }
  }, [events, push])
}
