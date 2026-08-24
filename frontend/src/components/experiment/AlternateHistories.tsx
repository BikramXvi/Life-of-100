import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { Panel } from '../ui/Panel'
import { ChartFrame } from '../ui/ChartFrame'
import { useSimulationList } from '../../lib/hooks'
import { api } from '../../lib/api'
import type { SimulationCompareResult } from '../../lib/types'
import { ComposedChart, Bar, Scatter, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid } from 'recharts'

/** SRS §27/§28/§29 — branch the active simulation into an independent
 * timeline, visualize every timeline's span and fork point, and diff two
 * timelines' recorded events to see how one changed decision rippled out.
 * Ported from the Streamlit dashboard's ALTERNATE HISTORIES tab, which the
 * React rewrite never carried over. */
export function AlternateHistories() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const { data: list } = useSimulationList()
  const sims = list?.simulations ?? []
  const activeId = list?.active_simulation_id

  const [newId, setNewId] = useState('')
  const [branching, setBranching] = useState(false)
  const [branchMsg, setBranchMsg] = useState<string | null>(null)
  const [activating, setActivating] = useState<string | null>(null)
  const [simA, setSimA] = useState('')
  const [simB, setSimB] = useState('')
  const [compareResult, setCompareResult] = useState<SimulationCompareResult | null>(null)
  const [comparing, setComparing] = useState(false)

  // Pre-fill sensible defaults once the registry loads, without stomping on
  // whatever the user has already typed/picked.
  useEffect(() => {
    if (!newId && activeId) setNewId(`${activeId}_branch`)
  }, [activeId, newId])
  useEffect(() => {
    if (sims.length >= 2 && !simA && !simB) {
      setSimA(sims[0].simulation_id)
      setSimB(sims[1].simulation_id)
    }
  }, [sims, simA, simB])

  async function doBranch() {
    setBranching(true)
    setBranchMsg(null)
    try {
      const res = await api.post<{ simulation_id: string; parent_simulation_id: string; branch_point_day: number }>(
        '/simulation/branch',
        { new_simulation_id: newId },
      )
      setBranchMsg(`Branched "${res.parent_simulation_id}" → "${res.simulation_id}" at day ${res.branch_point_day}.`)
      setNewId('')
      await qc.invalidateQueries({ queryKey: ['simulation-list'] })
    } catch (err) {
      setBranchMsg(String(err))
    } finally {
      setBranching(false)
    }
  }

  async function doActivate(id: string) {
    setActivating(id)
    try {
      await api.post(`/simulation/activate/${id}`)
      // Switching the active timeline changes basically every endpoint's
      // answer (status, citizens, events, ...) -- refetch everything.
      await qc.invalidateQueries()
    } finally {
      setActivating(null)
    }
  }

  async function doCompare() {
    if (!simA || !simB || simA === simB) return
    setComparing(true)
    try {
      const res = await api.get<SimulationCompareResult>(
        `/simulation/compare?simulation_a=${encodeURIComponent(simA)}&simulation_b=${encodeURIComponent(simB)}`,
      )
      setCompareResult(res)
    } catch (err) {
      alert(String(err))
    } finally {
      setComparing(false)
    }
  }

  const timelineData = sims.map((s) => ({
    id: s.simulation_id,
    start: s.branch_info?.branch_point_day ?? 0,
    span: Math.max(0, s.day - (s.branch_info?.branch_point_day ?? 0)),
    forkDay: s.branch_info ? s.branch_info.branch_point_day : undefined,
  }))

  const timelineCsv = sims.map((s) => ({
    simulation_id: s.simulation_id,
    day: s.day,
    population: s.population,
    parent_simulation_id: s.branch_info?.parent_simulation_id ?? '',
    branch_point_day: s.branch_info?.branch_point_day ?? '',
  }))

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-[320px_1fr] gap-3">
        <Panel title="Branch a Timeline" subtitle="Snapshot the active simulation into an independent branch you can nudge differently.">
          <label className="mb-1 block text-[11px] uppercase tracking-wide text-[var(--text-tertiary)]">New simulation ID</label>
          <input
            value={newId}
            onChange={(e) => setNewId(e.target.value)}
            placeholder="e.g. sim_001_food_subsidy"
            className="mb-3 w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-2.5 py-1.5 font-mono text-[12px] outline-none focus:border-[var(--accent)]"
          />
          <button
            onClick={doBranch}
            disabled={branching || !newId}
            className="w-full rounded-md bg-[var(--accent)] px-3 py-2 text-[12.5px] font-semibold text-[var(--accent-fg)] disabled:opacity-50"
          >
            {branching ? 'Branching…' : `Branch from ${activeId ?? '…'}`}
          </button>
          {branchMsg && (
            <div className="mt-3 rounded-md border border-[var(--border)] bg-[var(--bg)] p-2 text-[11.5px] leading-relaxed text-[var(--text-secondary)]">
              {branchMsg}
            </div>
          )}
        </Panel>

        <Panel title="Timelines" subtitle="Each bar spans its fork point → current day. Diamond marks where it branched off.">
          <ChartFrame height={Math.max(140, sims.length * 42 + 40)} csvData={timelineCsv} csvFilename="timelines.csv" pngFilename="timelines.png">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={timelineData} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 4 }}>
                <CartesianGrid stroke="var(--border)" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} />
                <YAxis dataKey="id" type="category" tick={{ fontSize: 10.5, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} width={110} />
                <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 12 }} />
                <Bar dataKey="start" stackId="t" fill="transparent" isAnimationActive={false} />
                <Bar dataKey="span" stackId="t" fill="var(--accent)" radius={[3, 3, 3, 3]} isAnimationActive={false} name="day range" />
                <Scatter dataKey="forkDay" fill="var(--danger)" shape="diamond" name="fork point" />
              </ComposedChart>
            </ResponsiveContainer>
          </ChartFrame>
        </Panel>
      </div>

      <Panel title="Timeline Registry" padded={false}>
        <div className="overflow-x-auto">
          <table className="w-full text-[12.5px]">
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-[10.5px] uppercase tracking-wide text-[var(--text-tertiary)]">
                <th className="px-3 py-2">Simulation</th>
                <th className="px-3 py-2">Day</th>
                <th className="px-3 py-2">Population</th>
                <th className="px-3 py-2">Parent</th>
                <th className="px-3 py-2">Forked at day</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              {sims.map((s) => (
                <tr key={s.simulation_id} className="border-b border-[var(--border)]">
                  <td className="px-3 py-2 font-mono">
                    {s.simulation_id}
                    {s.simulation_id === activeId && (
                      <span className="ml-2 rounded border border-[var(--accent)] px-1.5 py-0.5 text-[9.5px] font-semibold text-[var(--accent)]">ACTIVE</span>
                    )}
                  </td>
                  <td className="px-3 py-2 tabular-nums">{s.day}</td>
                  <td className="px-3 py-2 tabular-nums">{s.population}</td>
                  <td className="px-3 py-2 font-mono text-[var(--text-tertiary)]">{s.branch_info?.parent_simulation_id ?? '—'}</td>
                  <td className="px-3 py-2 tabular-nums">{s.branch_info?.branch_point_day ?? '—'}</td>
                  <td className="px-3 py-2 text-right">
                    {s.simulation_id !== activeId && (
                      <button
                        onClick={() => doActivate(s.simulation_id)}
                        disabled={activating === s.simulation_id}
                        className="rounded border border-[var(--border-strong)] px-2 py-1 text-[11px] font-medium text-[var(--accent)] hover:bg-[var(--accent-dim)] disabled:opacity-50"
                      >
                        {activating === s.simulation_id ? 'Activating…' : 'Set active'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {sims.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-3 py-4 text-center text-[var(--text-tertiary)]">
                    No simulations yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel title="Compare Two Timelines" subtitle="Metrics side-by-side, plus every event that only happened in one of them.">
        <div className="mb-4 flex flex-wrap items-end gap-3">
          <div>
            <label className="mb-1 block text-[11px] uppercase tracking-wide text-[var(--text-tertiary)]">Timeline A</label>
            <select value={simA} onChange={(e) => setSimA(e.target.value)} className="rounded-md border border-[var(--border)] bg-[var(--bg)] px-2.5 py-1.5 text-[12px]">
              {sims.map((s) => <option key={s.simulation_id} value={s.simulation_id}>{s.simulation_id}</option>)}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-[11px] uppercase tracking-wide text-[var(--text-tertiary)]">Timeline B</label>
            <select value={simB} onChange={(e) => setSimB(e.target.value)} className="rounded-md border border-[var(--border)] bg-[var(--bg)] px-2.5 py-1.5 text-[12px]">
              {sims.map((s) => <option key={s.simulation_id} value={s.simulation_id}>{s.simulation_id}</option>)}
            </select>
          </div>
          <button
            onClick={doCompare}
            disabled={comparing || !simA || !simB || simA === simB}
            className="rounded-md bg-[var(--accent)] px-3 py-1.5 text-[12.5px] font-semibold text-[var(--accent-fg)] disabled:opacity-50"
          >
            {comparing ? 'Comparing…' : 'Compare'}
          </button>
          {simA && simA === simB && <span className="text-[12px] text-[var(--warning)]">Pick two different timelines.</span>}
        </div>

        {compareResult && (
          <>
            <div className="mb-5 grid grid-cols-2 gap-4">
              {[compareResult.simulation_a, compareResult.simulation_b].map((w) => (
                <div key={w.simulation_id}>
                  <div className="mb-2 font-mono text-[13px] font-semibold">{w.simulation_id}</div>
                  {Object.entries(w.metrics).map(([k, v]) => (
                    <div key={k} className="flex justify-between border-b border-[var(--border)] py-1 text-[12px]">
                      <span className="text-[var(--text-tertiary)]">{k.replace(/_/g, ' ')}</span>
                      <span className="font-mono tabular-nums">{typeof v === 'number' ? v.toLocaleString() : String(v)}</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>

            <div className="grid grid-cols-2 gap-4">
              {[compareResult.simulation_a.simulation_id, compareResult.simulation_b.simulation_id].map((id) => (
                <div key={id}>
                  <div className="mb-1.5 text-[10.5px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
                    Only in {id} ({compareResult.divergent_events[id]?.length ?? 0})
                  </div>
                  <div className="max-h-[240px] overflow-y-auto">
                    {(compareResult.divergent_events[id] ?? []).map((e) => (
                      <button
                        key={e.event_id}
                        onClick={() => navigate(`/investigate?trace=${encodeURIComponent(e.event_id)}&sim=${encodeURIComponent(id)}`)}
                        className="flex w-full items-center justify-between border-b border-[var(--border)] py-1.5 text-left font-mono text-[11.5px] hover:text-[var(--accent)]"
                      >
                        <span>D{Math.floor(e.simulation_tick / 24)} · {e.event_type}</span>
                        <span className="text-[var(--text-tertiary)]">{e.source_entity}</span>
                      </button>
                    ))}
                    {(compareResult.divergent_events[id] ?? []).length === 0 && (
                      <div className="py-2 text-[12px] text-[var(--text-tertiary)]">No divergent events.</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </Panel>
    </div>
  )
}
