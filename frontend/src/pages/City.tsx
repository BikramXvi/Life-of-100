import { useEffect, useMemo, useState } from 'react'
import { Play, Pause, SkipForward, AlertTriangle } from 'lucide-react'
import { Breadcrumbs } from '../components/ui/Breadcrumbs'
import { Kpi } from '../components/ui/Kpi'
import { Panel } from '../components/ui/Panel'
import { Drawer, DrawerRow } from '../components/ui/Drawer'
import { CityMap, VIZ_MODES, type VizMode } from '../components/city/CityMap'
import {
  useStatus,
  useWorld,
  useHouseholds,
  useBusinesses,
  useCitizens,
  useEvents,
  useMetricsSeries,
} from '../lib/hooks'
import { api } from '../lib/api'
import { useQueryClient } from '@tanstack/react-query'
import clsx from 'clsx'

const EVENT_LEVEL: Record<string, 'alert' | 'ok' | 'info'> = {
  JOB_LOST: 'alert',
  BUSINESS_FAILED: 'alert',
  DISASTER_STARTED: 'alert',
  HEALTH_IMPACTED: 'alert',
  CITIZEN_DIED: 'alert',
  DIVORCE: 'alert',
  JOB_STARTED: 'ok',
  BUSINESS_EXPANDED: 'ok',
  MARRIAGE: 'ok',
  CHILD_BORN: 'ok',
  DISASTER_ENDED: 'ok',
  POLICY_CHANGED: 'ok',
}

export default function City() {
  const { data: status } = useStatus()
  const { data: world } = useWorld()
  const { data: households } = useHouseholds()
  const { data: businesses } = useBusinesses()
  const { data: citizens } = useCitizens()
  const { data: events } = useEvents(200)
  const { data: series } = useMetricsSeries()
  const qc = useQueryClient()

  const [mode, setMode] = useState<VizMode>('standard')
  const [selected, setSelected] = useState<{ id: string; kind: string } | null>(null)
  const [playing, setPlaying] = useState(false)
  const [advancing, setAdvancing] = useState(false)

  const householdByBuilding = useMemo(
    () => new Map((households ?? []).filter((h) => h.home_building_id).map((h) => [h.home_building_id!, h])),
    [households],
  )
  const businessByBuilding = useMemo(() => new Map((businesses ?? []).map((b) => [b.building_id, b])), [businesses])

  async function advance(days: number) {
    setAdvancing(true)
    try {
      await api.post('/simulation/tick', { ticks: 0, days })
      await qc.invalidateQueries()
    } finally {
      setAdvancing(false)
    }
  }

  async function togglePlay() {
    if (playing) {
      setPlaying(false)
      return
    }
    setPlaying(true)
  }

  // Real auto-advance loop while "playing" -- one real day per tick, not a
  // decorative animation. Must be useEffect, not useMemo: React only ever
  // invokes a cleanup function returned from useEffect, so a useMemo-based
  // version here would leak an uncancellable infinite loop the moment
  // `playing` becomes true, surviving even navigating away from this page.
  useEffect(() => {
    if (!playing) return
    let cancelled = false
    const loop = async () => {
      while (!cancelled) {
        await api.post('/simulation/tick', { ticks: 0, days: 1 })
        await qc.invalidateQueries()
        await new Promise((r) => setTimeout(r, 1400))
      }
    }
    loop()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing])

  const employmentSeries = series?.map((p) => (p.population ? (p.employed / p.population) * 100 : 0))
  const totalWealth = (citizens ?? []).reduce((s, c) => s + c.savings - c.debt, 0)
  const avgStress = households?.length ? households.reduce((s, h) => s + h.financial_stress, 0) / households.length : 0
  const eventsToday = (events ?? []).filter((e) => status && Math.floor(e.simulation_tick / 24) === status.day).length

  return (
    <div className="flex h-full flex-col">
      <Breadcrumbs items={[{ label: 'City' }]} />

      <div className="grid shrink-0 grid-cols-3 gap-3 px-6 pt-4 lg:grid-cols-6">
        <Kpi label="Population" value={String(status?.population ?? '—')} series={series?.map((p) => p.population)} />
        <Kpi
          label="Employment"
          value={status ? `${(100 - status.unemployment_rate * 100).toFixed(1)}%` : '—'}
          series={employmentSeries}
          color="var(--success)"
        />
        <Kpi label="Total Wealth" value={`NPR ${(totalWealth / 1e6).toFixed(2)}M`} color="var(--teal)" />
        <Kpi
          label="Financial Stress"
          value={`${(avgStress * 100).toFixed(1)}%`}
          color="var(--warning)"
          delta={avgStress > 0.5 ? { text: 'elevated', positive: false } : null}
        />
        <Kpi label="Businesses" value={String(status?.active_businesses ?? '—')} series={series?.map((p) => p.active_businesses)} color="var(--violet)" />
        <Kpi label="Events Today" value={String(eventsToday)} color="var(--accent)" />
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-[1fr_320px] gap-3 px-6 py-4">
        <div className="relative min-h-0">
          {world && households && businesses && citizens ? (
            <CityMap
              world={world}
              households={households}
              businesses={businesses}
              citizens={citizens}
              mode={mode}
              onSelectBuilding={(id, kind) => setSelected({ id, kind })}
            />
          ) : (
            <div className="flex h-full items-center justify-center rounded-[var(--radius-lg)] border border-[var(--border)] text-[13px] text-[var(--text-tertiary)]">
              Loading sector data…
            </div>
          )}

          {/* Floating visualization-mode control panel */}
          <div className="absolute left-3 top-3 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--bg-elevated)]/95 p-1.5 backdrop-blur">
            <div className="flex flex-col gap-0.5">
              {VIZ_MODES.map((m) => (
                <button
                  key={m.id}
                  onClick={() => setMode(m.id)}
                  className={clsx(
                    'rounded px-2.5 py-1.5 text-left text-[11.5px] font-medium transition-colors',
                    mode === m.id
                      ? 'bg-[var(--accent-dim)] text-[var(--accent)]'
                      : 'text-[var(--text-secondary)] hover:bg-[var(--surface-hover)]',
                  )}
                >
                  {m.label}
                </button>
              ))}
            </div>
          </div>

          <div className="absolute bottom-3 left-3 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--bg-elevated)]/95 px-3 py-2 text-[11px] text-[var(--text-tertiary)] backdrop-blur">
            {world?.city_id} — seed {world?.seed} — drag to orbit, scroll to zoom, click a building
          </div>
        </div>

        <Panel title="Terminal // Events" padded={false} className="flex min-h-0 flex-col">
          <div className="min-h-0 flex-1 overflow-y-auto p-2">
            {(events ?? []).slice(0, 40).map((e) => {
              const level = EVENT_LEVEL[e.event_type] ?? 'info'
              const day = Math.floor(e.simulation_tick / 24)
              const hour = e.simulation_tick % 24
              return (
                <div key={e.event_id} className="animate-fade-in flex items-start gap-2 border-b border-[var(--border)] px-2 py-1.5 font-mono text-[11px]">
                  <span className="shrink-0 text-[var(--text-tertiary)]">
                    D{String(day).padStart(3, '0')}.{String(hour).padStart(2, '0')}
                  </span>
                  <span
                    className={clsx(
                      level === 'alert' && 'text-[var(--danger)]',
                      level === 'ok' && 'text-[var(--success)]',
                      level === 'info' && 'text-[var(--text-secondary)]',
                    )}
                  >
                    {e.event_type.replace(/_/g, ' ')} — {e.source_entity}
                  </span>
                </div>
              )
            })}
          </div>
        </Panel>
      </div>

      {/* Time control dock */}
      <div className="flex shrink-0 items-center gap-4 border-t border-[var(--border)] bg-[var(--bg-elevated)] px-6 py-2.5">
        <button
          onClick={togglePlay}
          className="flex items-center gap-1.5 rounded-md border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1.5 text-[12px] font-medium hover:border-[var(--border-strong)]"
        >
          {playing ? <Pause size={13} /> : <Play size={13} />}
          {playing ? 'Pause' : 'Play'}
        </button>
        <button
          onClick={() => advance(1)}
          disabled={advancing || playing}
          className="flex items-center gap-1.5 rounded-md border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1.5 text-[12px] font-medium hover:border-[var(--border-strong)] disabled:opacity-40"
        >
          <SkipForward size={13} /> +1 Day
        </button>
        <button
          onClick={() => advance(5)}
          disabled={advancing || playing}
          className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1.5 text-[12px] font-medium hover:border-[var(--border-strong)] disabled:opacity-40"
        >
          +5 Days
        </button>
        <button
          onClick={() => advance(30)}
          disabled={advancing || playing}
          className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1.5 text-[12px] font-medium hover:border-[var(--border-strong)] disabled:opacity-40"
        >
          +30 Days
        </button>

        <div className="mx-2 h-6 w-px bg-[var(--border)]" />

        <span className="font-mono text-[12.5px] tabular-nums text-[var(--text-secondary)]">
          DAY {status?.day ?? '—'} · TICK {status?.tick.toLocaleString() ?? '—'}
        </span>

        {status && status.active_disasters.length > 0 && (
          <span className="flex items-center gap-1.5 rounded-md bg-[var(--danger)]/10 px-2.5 py-1 text-[11.5px] font-medium text-[var(--danger)]">
            <AlertTriangle size={13} />
            {status.active_disasters.join(', ').toUpperCase()} ACTIVE
          </span>
        )}
      </div>

      <Drawer
        open={!!selected}
        onClose={() => setSelected(null)}
        title={selected?.id ?? ''}
        subtitle={selected?.kind}
      >
        {selected?.kind === 'home' &&
          (() => {
            const hh = householdByBuilding.get(selected.id)
            if (!hh) return <div className="text-[13px] text-[var(--text-tertiary)]">Vacant home.</div>
            return (
              <div>
                <DrawerRow label="Members" value={hh.member_ids.length} />
                <DrawerRow label="Financial stress" value={`${(hh.financial_stress * 100).toFixed(0)}%`} />
                <DrawerRow label="Savings" value={hh.savings.toLocaleString()} />
                <DrawerRow label="Income" value={hh.income.toLocaleString()} />
                <DrawerRow label="Expenses" value={hh.expenses.toLocaleString()} />
                <a
                  href={`/people?scope=households&id=${hh.household_id}`}
                  className="mt-4 block rounded-md border border-[var(--border-strong)] px-3 py-2 text-center text-[12.5px] font-medium text-[var(--accent)] hover:bg-[var(--accent-dim)]"
                >
                  View full household →
                </a>
              </div>
            )
          })()}
        {selected?.kind !== 'home' &&
          (() => {
            const biz = businessByBuilding.get(selected?.id ?? '')
            if (!biz) return <div className="text-[13px] text-[var(--text-tertiary)]">No business record for this building.</div>
            return (
              <div>
                <DrawerRow label="Industry" value={biz.industry.replace(/_/g, ' ')} />
                <DrawerRow label="Status" value={biz.active ? 'Active' : 'Inactive'} />
                <DrawerRow label="Cash" value={biz.cash.toLocaleString()} />
                <DrawerRow label="Employees" value={biz.headcount} />
                <DrawerRow label="Revenue" value={biz.revenue.toLocaleString()} />
                <DrawerRow label="Profit" value={biz.profit.toLocaleString()} />
              </div>
            )
          })()}
      </Drawer>
    </div>
  )
}
