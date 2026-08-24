import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { GitBranch } from 'lucide-react'
import { Breadcrumbs } from '../components/ui/Breadcrumbs'
import { Panel } from '../components/ui/Panel'
import { api } from '../lib/api'
import { useStatus } from '../lib/hooks'

interface SimRow {
  simulation_id: string
  tick: number
  day: number
  population: number
  branch_info: { parent_simulation_id: string; branch_point_tick: number; branch_point_day: number } | null
}

export default function Timelines() {
  const { data: status } = useStatus()
  const qc = useQueryClient()
  const { data } = useQuery({
    queryKey: ['simulation-list'],
    queryFn: () => api.get<{ active_simulation_id: string; simulations: SimRow[] }>('/simulation/list'),
    refetchInterval: 5000,
  })
  const [newId, setNewId] = useState('')
  const [a, setA] = useState('')
  const [b, setB] = useState('')
  const [comparison, setComparison] = useState<any>(null)

  const rows = data?.simulations ?? []
  const maxDay = Math.max(1, ...rows.map((r) => r.day))

  async function branch() {
    if (!newId) return
    await api.post('/simulation/branch', { new_simulation_id: newId })
    setNewId('')
    await qc.invalidateQueries({ queryKey: ['simulation-list'] })
  }

  async function activate(id: string) {
    await api.post(`/simulation/activate/${id}`)
    await qc.invalidateQueries()
  }

  async function compare() {
    if (!a || !b) return
    const res = await api.get(`/simulation/compare?simulation_a=${a}&simulation_b=${b}`)
    setComparison(res)
  }

  return (
    <div className="flex h-full flex-col">
      <Breadcrumbs items={[{ label: 'Timelines' }]} />
      <div className="flex flex-col gap-3 px-6 py-4">
        <Panel title="Branching Timeline" subtitle={`Active: ${data?.active_simulation_id ?? '—'}`}>
          <div className="mb-4 flex gap-2">
            <input
              value={newId}
              onChange={(e) => setNewId(e.target.value)}
              placeholder={`${status?.simulation_id ?? 'sim'}_branch`}
              className="flex-1 rounded-md border border-[var(--border)] bg-[var(--bg)] px-2.5 py-1.5 text-[12px] outline-none focus:border-[var(--accent)]"
            />
            <button onClick={branch} className="flex items-center gap-1.5 rounded-md bg-[var(--accent)] px-3 py-1.5 text-[12px] font-semibold text-[var(--accent-fg)]">
              <GitBranch size={13} /> Branch
            </button>
          </div>

          <div className="space-y-2">
            {rows.map((r) => {
              const start = r.branch_info?.branch_point_day ?? 0
              const widthPct = ((r.day - start) / maxDay) * 100
              const startPct = (start / maxDay) * 100
              return (
                <div key={r.simulation_id} className="flex items-center gap-3">
                  <span className={`w-40 shrink-0 truncate font-mono text-[11px] ${r.simulation_id === data?.active_simulation_id ? 'text-[var(--accent)] font-semibold' : 'text-[var(--text-secondary)]'}`}>
                    {r.simulation_id}
                  </span>
                  <div className="relative h-4 flex-1 rounded bg-[var(--border)]/40">
                    <div
                      className="absolute h-full rounded bg-[var(--accent)]"
                      style={{ left: `${startPct}%`, width: `${Math.max(1, widthPct)}%` }}
                    />
                    {r.branch_info && (
                      <div className="absolute top-[-2px] h-5 w-0.5 bg-[var(--danger)]" style={{ left: `${startPct}%` }} title={`forked day ${start}`} />
                    )}
                  </div>
                  <span className="w-14 shrink-0 text-right font-mono text-[10.5px] text-[var(--text-tertiary)]">day {r.day}</span>
                  <button onClick={() => activate(r.simulation_id)} className="shrink-0 rounded border border-[var(--border)] px-2 py-0.5 text-[10.5px] hover:border-[var(--accent)] hover:text-[var(--accent)]">
                    activate
                  </button>
                </div>
              )
            })}
          </div>
        </Panel>

        <Panel title="Compare Two Timelines">
          <div className="mb-3 flex gap-2">
            <select value={a} onChange={(e) => setA(e.target.value)} className="flex-1 rounded-md border border-[var(--border)] bg-[var(--bg)] px-2.5 py-1.5 text-[12px]">
              <option value="">Timeline A…</option>
              {rows.map((r) => <option key={r.simulation_id} value={r.simulation_id}>{r.simulation_id}</option>)}
            </select>
            <select value={b} onChange={(e) => setB(e.target.value)} className="flex-1 rounded-md border border-[var(--border)] bg-[var(--bg)] px-2.5 py-1.5 text-[12px]">
              <option value="">Timeline B…</option>
              {rows.map((r) => <option key={r.simulation_id} value={r.simulation_id}>{r.simulation_id}</option>)}
            </select>
            <button onClick={compare} disabled={!a || !b} className="rounded-md bg-[var(--accent)] px-3 py-1.5 text-[12px] font-semibold text-[var(--accent-fg)] disabled:opacity-50">
              Compare
            </button>
          </div>
          {comparison && (
            <div className="grid grid-cols-2 gap-3">
              <pre className="overflow-x-auto rounded-md border border-[var(--border)] bg-[var(--bg)] p-3 text-[11px]">
                {JSON.stringify(comparison.simulation_a?.metrics, null, 2)}
              </pre>
              <pre className="overflow-x-auto rounded-md border border-[var(--border)] bg-[var(--bg)] p-3 text-[11px]">
                {JSON.stringify(comparison.simulation_b?.metrics, null, 2)}
              </pre>
            </div>
          )}
        </Panel>
      </div>
    </div>
  )
}
