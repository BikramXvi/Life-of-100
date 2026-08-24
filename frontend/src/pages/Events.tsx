import { useMemo, useState } from 'react'
import { Breadcrumbs } from '../components/ui/Breadcrumbs'
import { Panel } from '../components/ui/Panel'
import { useEvents } from '../lib/hooks'
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid } from 'recharts'

export default function Events() {
  const { data: events } = useEvents(500)
  const [typeFilter, setTypeFilter] = useState<string>('ALL')
  const [search, setSearch] = useState('')

  const types = useMemo(() => Array.from(new Set((events ?? []).map((e) => e.event_type))).sort(), [events])

  const filtered = useMemo(() => {
    return (events ?? []).filter((e) => {
      if (typeFilter !== 'ALL' && e.event_type !== typeFilter) return false
      if (search && !e.event_id.includes(search) && !e.source_entity.includes(search)) return false
      return true
    })
  }, [events, typeFilter, search])

  const density = useMemo(() => {
    const byDay = new Map<number, number>()
    for (const e of events ?? []) {
      const day = Math.floor(e.simulation_tick / 24)
      byDay.set(day, (byDay.get(day) ?? 0) + 1)
    }
    return Array.from(byDay.entries()).map(([day, count]) => ({ day, count })).sort((a, b) => a.day - b.day)
  }, [events])

  return (
    <div className="flex h-full flex-col">
      <Breadcrumbs items={[{ label: 'Events' }]} />
      <div className="flex flex-col gap-3 px-6 py-4">
        <Panel title="Event Density" subtitle="Last 500 events, bucketed by day">
          <div className="h-[140px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={density}>
                <CartesianGrid stroke="var(--border)" vertical={false} />
                <XAxis dataKey="day" tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 12 }} />
                <Bar dataKey="count" fill="var(--accent)" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel title="Event Explorer" padded={false}>
          <div className="flex items-center gap-2 border-b border-[var(--border)] p-2">
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search event_id or entity…"
              className="flex-1 rounded-md border border-[var(--border)] bg-[var(--bg)] px-2.5 py-1.5 text-[12px] outline-none focus:border-[var(--accent)]"
            />
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="rounded-md border border-[var(--border)] bg-[var(--bg)] px-2.5 py-1.5 text-[12px]"
            >
              <option value="ALL">All types</option>
              {types.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
          <div className="max-h-[420px] overflow-y-auto overflow-x-auto">
            <table className="w-full text-[12px]">
              <thead className="sticky top-0 bg-[var(--surface)]">
                <tr className="border-b border-[var(--border)] text-left text-[10.5px] uppercase tracking-wide text-[var(--text-tertiary)]">
                  <th className="px-3 py-2">Day</th>
                  <th className="px-3 py-2">Type</th>
                  <th className="px-3 py-2">Entity</th>
                  <th className="px-3 py-2">Source</th>
                  <th className="px-3 py-2">Tick</th>
                  <th className="px-3 py-2">Event ID</th>
                </tr>
              </thead>
              <tbody>
                {filtered.slice(0, 200).map((e) => (
                  <tr key={e.event_id} className="border-b border-[var(--border)] hover:bg-[var(--surface-hover)]">
                    <td className="px-3 py-1.5 font-mono">{Math.floor(e.simulation_tick / 24)}</td>
                    <td className="px-3 py-1.5">{e.event_type}</td>
                    <td className="px-3 py-1.5 font-mono">{e.source_entity}</td>
                    <td className="px-3 py-1.5 text-[var(--text-tertiary)]">{e.source_type}</td>
                    <td className="px-3 py-1.5 font-mono tabular-nums">{e.simulation_tick}</td>
                    <td className="px-3 py-1.5 font-mono text-[var(--text-tertiary)]">{e.event_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </div>
    </div>
  )
}
