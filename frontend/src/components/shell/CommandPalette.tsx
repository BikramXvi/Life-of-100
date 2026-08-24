import { useState } from 'react'
import { Command } from 'cmdk'
import { useNavigate } from 'react-router-dom'
import { useCitizens, useHouseholds, useBusinesses } from '../../lib/hooks'
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
  ArrowRight,
} from 'lucide-react'

export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const navigate = useNavigate()
  const { data: citizens } = useCitizens()
  const { data: households } = useHouseholds()
  const { data: businesses } = useBusinesses()
  const [query, setQuery] = useState('')

  function go(path: string) {
    navigate(path)
    onClose()
  }

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 pt-[14vh]"
      onClick={onClose}
    >
      <div className="animate-fade-in w-full max-w-xl overflow-hidden rounded-lg border border-[var(--border-strong)] bg-[var(--bg-elevated)] shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <Command label="Command palette" className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider [&_[cmdk-group-heading]]:text-[var(--text-tertiary)]">
          <div className="flex items-center gap-2 border-b border-[var(--border)] px-3">
            <Search size={15} className="text-[var(--text-tertiary)]" />
            <Command.Input
              autoFocus
              value={query}
              onValueChange={setQuery}
              placeholder="Search citizens, households, businesses, or jump to a page…"
              className="w-full bg-transparent py-3 text-[13.5px] text-[var(--text-primary)] outline-none placeholder:text-[var(--text-tertiary)]"
            />
            <kbd className="rounded border border-[var(--border-strong)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--text-tertiary)]">esc</kbd>
          </div>
          <Command.List className="max-h-[420px] overflow-y-auto p-1.5">
            <Command.Empty className="px-3 py-6 text-center text-[13px] text-[var(--text-tertiary)]">
              No results found.
            </Command.Empty>

            {query.trim() && (
              <Command.Group heading="Search">
                <Command.Item
                  value={`zzz-see-all-results ${query}`}
                  onSelect={() => go(`/search?q=${encodeURIComponent(query.trim())}`)}
                  className="flex cursor-pointer items-center justify-between rounded-md px-3 py-2 text-[13px] text-[var(--accent)] aria-selected:bg-[var(--surface-hover)]"
                >
                  <span>See all results for "{query.trim()}"</span>
                  <ArrowRight size={14} />
                </Command.Item>
              </Command.Group>
            )}

            <Command.Group heading="Navigate">
              {[
                { to: '/city', label: 'Go to City', icon: Building2 },
                { to: '/experiment', label: 'Open Experiment Lab', icon: FlaskConical },
                { to: '/investigate', label: 'Open Investigate', icon: Search },
                { to: '/people', label: 'Open People', icon: Users },
                { to: '/events', label: 'Open Event Explorer', icon: Calendar },
                { to: '/calendar', label: 'Open Calendar', icon: CalendarDays },
                { to: '/disasters', label: 'Open Disaster Control', icon: AlertTriangle },
                { to: '/ai-agents', label: 'Open AI Governance', icon: Bot },
                { to: '/analytics', label: 'Open Analytics', icon: BarChart3 },
                { to: '/timelines', label: 'Open Timelines', icon: GitBranch },
                { to: '/observability', label: 'View System Health', icon: Server },
              ].map((item) => (
                <Command.Item
                  key={item.to}
                  onSelect={() => go(item.to)}
                  className="flex cursor-pointer items-center gap-2.5 rounded-md px-3 py-2 text-[13px] text-[var(--text-secondary)] aria-selected:bg-[var(--surface-hover)] aria-selected:text-[var(--text-primary)]"
                >
                  <item.icon size={14} strokeWidth={1.75} />
                  {item.label}
                </Command.Item>
              ))}
            </Command.Group>

            {citizens && citizens.length > 0 && (
              <Command.Group heading="Citizens">
                {citizens.slice(0, 200).map((c) => (
                  <Command.Item
                    key={c.citizen_id}
                    value={`${c.name} ${c.citizen_id}`}
                    onSelect={() => go(`/people/${c.citizen_id}`)}
                    className="flex cursor-pointer items-center justify-between rounded-md px-3 py-2 text-[13px] text-[var(--text-secondary)] aria-selected:bg-[var(--surface-hover)] aria-selected:text-[var(--text-primary)]"
                  >
                    <span>{c.name}</span>
                    <span className="font-mono text-[11px] text-[var(--text-tertiary)]">{c.citizen_id}</span>
                  </Command.Item>
                ))}
              </Command.Group>
            )}

            {households && households.length > 0 && (
              <Command.Group heading="Households">
                {households.slice(0, 100).map((h) => (
                  <Command.Item
                    key={h.household_id}
                    value={h.household_id}
                    onSelect={() => go(`/people?scope=households&id=${h.household_id}`)}
                    className="flex cursor-pointer items-center gap-2.5 rounded-md px-3 py-2 text-[13px] text-[var(--text-secondary)] aria-selected:bg-[var(--surface-hover)] aria-selected:text-[var(--text-primary)]"
                  >
                    {h.household_id}
                  </Command.Item>
                ))}
              </Command.Group>
            )}

            {businesses && businesses.length > 0 && (
              <Command.Group heading="Businesses">
                {businesses.slice(0, 100).map((b) => (
                  <Command.Item
                    key={b.business_id}
                    value={`${b.business_id} ${b.industry}`}
                    onSelect={() => go(`/people?scope=businesses&id=${b.business_id}`)}
                    className="flex cursor-pointer items-center justify-between rounded-md px-3 py-2 text-[13px] text-[var(--text-secondary)] aria-selected:bg-[var(--surface-hover)] aria-selected:text-[var(--text-primary)]"
                  >
                    <span>{b.business_id}</span>
                    <span className="text-[11px] text-[var(--text-tertiary)]">{b.industry}</span>
                  </Command.Item>
                ))}
              </Command.Group>
            )}
          </Command.List>
        </Command>
      </div>
    </div>
  )
}
