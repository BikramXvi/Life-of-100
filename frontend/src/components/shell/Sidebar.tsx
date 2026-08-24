import { NavLink } from 'react-router-dom'
import {
  Building2,
  FlaskConical,
  Search,
  Users,
  Calendar,
  CalendarDays,
  AlertTriangle,
  Bot,
  BarChart3,
  GitBranch,
  Server,
  ChevronsLeft,
  ChevronsRight,
} from 'lucide-react'
import { useState } from 'react'
import clsx from 'clsx'
import { useStatus } from '../../lib/hooks'

const PRIMARY = [
  { to: '/city', label: 'City', icon: Building2 },
  { to: '/experiment', label: 'Experiment', icon: FlaskConical },
  { to: '/investigate', label: 'Investigate', icon: Search },
  { to: '/people', label: 'People', icon: Users },
]

const SECONDARY = [
  { to: '/events', label: 'Events', icon: Calendar },
  { to: '/calendar', label: 'Calendar', icon: CalendarDays },
  { to: '/disasters', label: 'Disasters', icon: AlertTriangle },
  { to: '/ai-agents', label: 'AI Agents', icon: Bot },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/timelines', label: 'Timelines', icon: GitBranch },
  { to: '/observability', label: 'Observability', icon: Server },
]

function NavItem({ to, label, icon: Icon, collapsed }: { to: string; label: string; icon: typeof Building2; collapsed: boolean }) {
  return (
    <NavLink
      to={to}
      title={collapsed ? label : undefined}
      className={({ isActive }) =>
        clsx(
          'group flex items-center gap-3 rounded-md px-2.5 py-2 text-[13px] font-medium transition-colors duration-100',
          isActive
            ? 'bg-[var(--accent-dim)] text-[var(--accent)]'
            : 'text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)]',
        )
      }
    >
      <Icon size={16} strokeWidth={1.75} className="shrink-0" />
      {!collapsed && <span>{label}</span>}
    </NavLink>
  )
}

function SystemStatusRow({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className="flex items-center justify-between px-2.5 py-1 text-[11px]">
      <span className="text-[var(--text-tertiary)] tracking-wide">{label}</span>
      <span
        className={clsx('h-1.5 w-1.5 rounded-full', ok ? 'bg-[var(--success)]' : 'bg-[var(--text-tertiary)]')}
      />
    </div>
  )
}

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const { data: status } = useStatus()

  return (
    <aside
      className={clsx(
        'flex h-full shrink-0 flex-col border-r border-[var(--border)] bg-[var(--bg-elevated)] transition-[width] duration-150',
        collapsed ? 'w-[56px]' : 'w-[220px]',
      )}
    >
      <div className="flex items-center justify-between px-3 py-3.5">
        {!collapsed && <span className="font-mono text-[15px] font-bold tracking-tight">LIFE/100</span>}
        <button
          onClick={() => setCollapsed((c) => !c)}
          className="rounded p-1 text-[var(--text-tertiary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)]"
          aria-label="Toggle sidebar"
        >
          {collapsed ? <ChevronsRight size={15} /> : <ChevronsLeft size={15} />}
        </button>
      </div>

      <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto px-2">
        {PRIMARY.map((item) => (
          <NavItem key={item.to} {...item} collapsed={collapsed} />
        ))}

        <div className={clsx('mt-4 mb-1 px-2.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]', collapsed && 'hidden')}>
          Analysis
        </div>
        {SECONDARY.map((item) => (
          <NavItem key={item.to} {...item} collapsed={collapsed} />
        ))}
      </nav>

      <div className="border-t border-[var(--border)] py-2">
        {!collapsed && (
          <div className="px-2.5 pb-1 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
            System Status
          </div>
        )}
        {collapsed ? (
          <div className="flex justify-center py-1">
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--success)]" />
          </div>
        ) : (
          <>
            <SystemStatusRow label="DATABASE" ok={true} />
            <SystemStatusRow label="REDPANDA" ok={true} />
            <SystemStatusRow label="SNOWFLAKE" ok={true} />
            <SystemStatusRow label="API" ok={!!status} />
          </>
        )}
      </div>
    </aside>
  )
}
