import { Bell, Moon, Search, Settings, Sun } from 'lucide-react'
import { useState } from 'react'
import { useStatus } from '../../lib/hooks'
import { useNotificationStore } from '../../lib/notifications'
import { useTheme } from '../../lib/useTheme'
import { NotificationsPanel } from './NotificationsPanel'

function StatSeg({ label, value }: { label: string; value: string | number }) {
  return (
    <span className="flex items-baseline gap-1.5 font-mono text-[12px]">
      <span className="text-[var(--text-tertiary)] uppercase tracking-wide">{label}</span>
      <span className="font-semibold text-[var(--text-primary)] tabular-nums">{value}</span>
    </span>
  )
}

export function TopBar({ onOpenPalette }: { onOpenPalette: () => void }) {
  const { data: status, isError } = useStatus()
  const [notifOpen, setNotifOpen] = useState(false)
  const unread = useNotificationStore((s) => s.notifications.filter((n) => !n.read).length)
  const { theme, toggle } = useTheme()

  return (
    <header className="flex h-12 shrink-0 items-center justify-between border-b border-[var(--border)] bg-[var(--bg-elevated)] px-4">
      <div className="flex items-center gap-5">
        {status ? (
          <>
            <StatSeg label="Day" value={status.day} />
            <StatSeg label="Tick" value={status.tick.toLocaleString()} />
            <StatSeg label="Pop" value={status.population} />
            <span className="flex items-center gap-1.5 text-[12px] font-medium">
              <span
                className={`live-dot h-1.5 w-1.5 rounded-full ${isError ? 'bg-[var(--danger)]' : 'bg-[var(--success)]'}`}
              />
              <span className="text-[var(--text-secondary)] tracking-wide">
                {isError ? 'DISCONNECTED' : 'SIMULATION LIVE'}
              </span>
            </span>
          </>
        ) : (
          <span className="text-[12px] text-[var(--text-tertiary)]">connecting…</span>
        )}
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={onOpenPalette}
          className="flex items-center gap-2 rounded-md border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1.5 text-[12px] text-[var(--text-tertiary)] hover:border-[var(--border-strong)] hover:text-[var(--text-secondary)]"
        >
          <Search size={13} />
          <span>Search…</span>
          <kbd className="ml-2 rounded border border-[var(--border-strong)] bg-[var(--bg)] px-1.5 py-0.5 font-mono text-[10px]">
            ⌘K
          </kbd>
        </button>
        <div className="relative">
          <button
            onClick={() => setNotifOpen((o) => !o)}
            className="relative rounded-md p-1.5 text-[var(--text-tertiary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)]"
            aria-label="Notifications"
          >
            <Bell size={16} strokeWidth={1.75} />
            {unread > 0 && (
              <span className="absolute -right-0.5 -top-0.5 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-[var(--danger)] text-[9px] font-bold text-white">
                {unread > 9 ? '9+' : unread}
              </span>
            )}
          </button>
          {notifOpen && <NotificationsPanel onClose={() => setNotifOpen(false)} />}
        </div>
        <button
          onClick={toggle}
          className="rounded-md p-1.5 text-[var(--text-tertiary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)]"
          aria-label="Toggle theme"
          title={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
        >
          {theme === 'dark' ? <Sun size={16} strokeWidth={1.75} /> : <Moon size={16} strokeWidth={1.75} />}
        </button>
        <button className="rounded-md p-1.5 text-[var(--text-tertiary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)]" aria-label="Settings">
          <Settings size={16} strokeWidth={1.75} />
        </button>
      </div>
    </header>
  )
}
