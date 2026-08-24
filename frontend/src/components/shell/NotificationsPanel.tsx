import { AlertTriangle, Info } from 'lucide-react'
import clsx from 'clsx'
import { useNotificationStore } from '../../lib/notifications'

export function NotificationsPanel({ onClose }: { onClose: () => void }) {
  const notifications = useNotificationStore((s) => s.notifications)
  const markAllRead = useNotificationStore((s) => s.markAllRead)

  return (
    <div className="fixed inset-0 z-40" onClick={onClose}>
      <div
        className="animate-fade-in absolute right-4 top-12 w-[340px] rounded-md border border-[var(--border-strong)] bg-[var(--bg-elevated)] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-[var(--border)] px-3 py-2.5">
          <span className="text-[12px] font-semibold uppercase tracking-wide text-[var(--text-secondary)]">Notifications</span>
          <button onClick={markAllRead} className="text-[11px] text-[var(--accent)] hover:underline">
            Mark all read
          </button>
        </div>
        <div className="max-h-[400px] overflow-y-auto">
          {notifications.length === 0 && (
            <div className="px-3 py-8 text-center text-[12.5px] text-[var(--text-tertiary)]">
              No notifications yet — advance time to generate events.
            </div>
          )}
          {notifications.map((n) => (
            <div key={n.id} className={clsx('flex gap-2.5 border-b border-[var(--border)] px-3 py-2.5', !n.read && 'bg-[var(--accent-dim)]/20')}>
              {n.level === 'info' ? (
                <Info size={14} className="mt-0.5 shrink-0 text-[var(--accent)]" />
              ) : (
                <AlertTriangle size={14} className={clsx('mt-0.5 shrink-0', n.level === 'critical' ? 'text-[var(--danger)]' : 'text-[var(--warning)]')} />
              )}
              <div>
                <div className="text-[12px] font-medium text-[var(--text-primary)]">{n.title}</div>
                <div className="mt-0.5 text-[11px] text-[var(--text-tertiary)]">{n.detail}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
