import { useQuery } from '@tanstack/react-query'
import { ArrowRight } from 'lucide-react'
import { Breadcrumbs } from '../components/ui/Breadcrumbs'
import { Panel } from '../components/ui/Panel'
import { Kpi } from '../components/ui/Kpi'
import { api } from '../lib/api'

interface ObsMetrics {
  simulation_id: string
  current_simulation_time: string
  tick: number
  ticks_per_second_1min_avg: number
  events_total: number
  active_citizens: number
  active_businesses: number
  active_disasters: string[]
  cpu_percent: number | null
  memory_mb: number | null
}

const PIPELINE = ['Simulation', 'Events', 'Redpanda', 'Worker', 'PostgreSQL', 'Snowflake']

export default function Observability() {
  const { data } = useQuery({
    queryKey: ['observability'],
    queryFn: () => api.get<ObsMetrics>('/observability/metrics'),
    refetchInterval: 5000,
  })

  return (
    <div className="flex h-full flex-col">
      <Breadcrumbs items={[{ label: 'Observability' }]} />
      <div className="flex flex-col gap-3 px-6 py-4">
        <Panel title="Data Pipeline">
          <div className="flex items-center justify-between overflow-x-auto py-4">
            {PIPELINE.map((node, i) => (
              <div key={node} className="flex items-center gap-3">
                <div className="flex flex-col items-center gap-1.5">
                  <div className="flex h-14 w-24 flex-col items-center justify-center rounded-md border border-[var(--success)]/40 bg-[var(--success)]/5">
                    <span className="live-dot mb-1 h-1.5 w-1.5 rounded-full bg-[var(--success)]" />
                    <span className="text-center text-[10.5px] font-medium">{node}</span>
                  </div>
                </div>
                {i < PIPELINE.length - 1 && <ArrowRight size={16} className="shrink-0 text-[var(--text-tertiary)]" />}
              </div>
            ))}
          </div>
          <p className="text-[11.5px] text-[var(--text-tertiary)]">
            Snowflake (and DuckDB, its local stand-in) sit outside the critical path — the simulation never depends on
            either responding to advance.
          </p>
        </Panel>

        <div className="grid grid-cols-4 gap-3">
          <Kpi label="Events Processed" value={data ? data.events_total.toLocaleString() : '—'} />
          <Kpi label="Ticks / sec (1min avg)" value={data ? data.ticks_per_second_1min_avg.toFixed(2) : '—'} color="var(--teal)" />
          <Kpi label="CPU" value={data?.cpu_percent != null ? `${data.cpu_percent.toFixed(1)}%` : '—'} color="var(--warning)" />
          <Kpi label="Memory" value={data?.memory_mb != null ? `${data.memory_mb.toFixed(0)} MB` : '—'} color="var(--violet)" />
        </div>

        <Panel title="Simulation Metadata">
          <div className="grid grid-cols-2 gap-x-8 gap-y-1.5 text-[12.5px]">
            <div className="flex justify-between border-b border-[var(--border)] py-1.5">
              <span className="text-[var(--text-tertiary)]">Simulation ID</span>
              <span className="font-mono">{data?.simulation_id ?? '—'}</span>
            </div>
            <div className="flex justify-between border-b border-[var(--border)] py-1.5">
              <span className="text-[var(--text-tertiary)]">Simulation time</span>
              <span className="font-mono">{data?.current_simulation_time ?? '—'}</span>
            </div>
            <div className="flex justify-between border-b border-[var(--border)] py-1.5">
              <span className="text-[var(--text-tertiary)]">Active citizens</span>
              <span className="font-mono">{data?.active_citizens ?? '—'}</span>
            </div>
            <div className="flex justify-between border-b border-[var(--border)] py-1.5">
              <span className="text-[var(--text-tertiary)]">Active businesses</span>
              <span className="font-mono">{data?.active_businesses ?? '—'}</span>
            </div>
          </div>
        </Panel>
      </div>
    </div>
  )
}
