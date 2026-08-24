import { useState } from 'react'
import { Breadcrumbs } from '../components/ui/Breadcrumbs'
import { Panel } from '../components/ui/Panel'
import { ChartFrame } from '../components/ui/ChartFrame'
import { AlternateHistories } from '../components/experiment/AlternateHistories'
import { api } from '../lib/api'
import type { ExperimentResult, SensitivityResult } from '../lib/types'
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid, LineChart, Line, ReferenceArea } from 'recharts'

const DISASTER_TYPES = ['drought', 'food_shortage', 'flood', 'earthquake', 'disease_outbreak', 'economic_recession', 'energy_crisis']

function Slider({ label, value, onChange, min, max, step }: { label: string; value: number; onChange: (v: number) => void; min: number; max: number; step: number }) {
  return (
    <label className="mb-3 block text-[12px]">
      <div className="mb-1 flex justify-between">
        <span className="text-[var(--text-tertiary)] uppercase tracking-wide">{label}</span>
        <span className="font-mono font-semibold">{value}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))} className="w-full accent-[var(--accent)]" />
    </label>
  )
}

function WhatIf() {
  const [disaster, setDisaster] = useState('drought')
  const [duration, setDuration] = useState(30)
  const [severity, setSeverity] = useState(0.4)
  const [ticks, setTicks] = useState(30)
  const [foodSubsidy, setFoodSubsidy] = useState(0.5)
  const [result, setResult] = useState<ExperimentResult | null>(null)
  const [busy, setBusy] = useState(false)

  async function run() {
    setBusy(true)
    try {
      const res = await api.post<ExperimentResult>('/experiments/run', {
        ticks,
        scenarios: [
          { name: 'World A — No Intervention', disaster, disaster_duration: duration, disaster_severity: severity },
          { name: 'World B — Food Subsidy', disaster, disaster_duration: duration, disaster_severity: severity, policies: { food_subsidy: foodSubsidy } },
          { name: 'World C — Emergency Employment', disaster, disaster_duration: duration, disaster_severity: severity, emergency_employment: true },
        ],
      })
      setResult(res)
    } finally {
      setBusy(false)
    }
  }

  const worlds = result
    ? [{ name: 'Control', metrics: result.control.metrics }, ...result.scenarios.map((s) => ({ name: s.name, metrics: s.metrics }))]
    : []
  const chartData = worlds.map((w) => ({ name: w.name.replace('World A — ', '').replace('World B — ', '').replace('World C — ', ''), unemployment: (w.metrics.unemployment_rate as number) * 100, business_failures: w.metrics.business_failures }))

  return (
    <div className="grid grid-cols-[340px_1fr] gap-3">
      <Panel title="Injection Parameters">
        <select value={disaster} onChange={(e) => setDisaster(e.target.value)} className="mb-3 w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-2.5 py-1.5 text-[12px]">
          {DISASTER_TYPES.map((d) => <option key={d} value={d}>{d.replace(/_/g, ' ')}</option>)}
        </select>
        <Slider label="Duration (days)" value={duration} onChange={setDuration} min={5} max={90} step={5} />
        <Slider label="Severity" value={severity} onChange={setSeverity} min={0.1} max={1} step={0.05} />
        <Slider label="Days to run" value={ticks} onChange={setTicks} min={5} max={90} step={5} />
        <Slider label="Food subsidy (World B)" value={foodSubsidy} onChange={setFoodSubsidy} min={0} max={1} step={0.05} />
        <button onClick={run} disabled={busy} className="mt-2 w-full rounded-md bg-[var(--accent)] px-3 py-2 text-[12.5px] font-semibold text-[var(--accent-fg)] disabled:opacity-50">
          {busy ? 'Running 3 futures…' : 'Run 3 Futures'}
        </button>
      </Panel>

      <Panel title="Impact Comparison">
        {result ? (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="mb-1 text-[11px] text-[var(--text-tertiary)]">Unemployment rate (%)</div>
              <ChartFrame csvData={chartData} csvFilename="whatif_unemployment.csv" pngFilename="whatif_unemployment.png">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData}>
                    <CartesianGrid stroke="var(--border)" vertical={false} />
                    <XAxis dataKey="name" tick={{ fontSize: 9, fill: 'var(--text-tertiary)' }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} interval={0} angle={-15} textAnchor="end" height={50} />
                    <YAxis tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 12 }} />
                    <Bar dataKey="unemployment" fill="var(--danger)" radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </ChartFrame>
            </div>
            <div>
              <div className="mb-1 text-[11px] text-[var(--text-tertiary)]">Business failures</div>
              <ChartFrame csvData={chartData} csvFilename="whatif_business_failures.csv" pngFilename="whatif_business_failures.png">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData}>
                    <CartesianGrid stroke="var(--border)" vertical={false} />
                    <XAxis dataKey="name" tick={{ fontSize: 9, fill: 'var(--text-tertiary)' }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} interval={0} angle={-15} textAnchor="end" height={50} />
                    <YAxis tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 12 }} />
                    <Bar dataKey="business_failures" fill="var(--warning)" radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </ChartFrame>
            </div>
          </div>
        ) : (
          <div className="text-[12.5px] text-[var(--text-tertiary)]">Run 3 futures to see the comparison.</div>
        )}
      </Panel>
    </div>
  )
}

function BreakingPoint() {
  const [min, setMin] = useState(0.05)
  const [max, setMax] = useState(0.5)
  const [steps, setSteps] = useState(10)
  const [days, setDays] = useState(15)
  const [result, setResult] = useState<SensitivityResult | null>(null)
  const [busy, setBusy] = useState(false)

  async function run() {
    setBusy(true)
    try {
      const stepSize = (max - min) / (steps - 1)
      const values = Array.from({ length: steps }, (_, i) => Number((min + i * stepSize).toFixed(4)))
      const res = await api.post<SensitivityResult>('/experiments/sensitivity', { parameter: 'drought_severity', values, ticks: days })
      setResult(res)
    } finally {
      setBusy(false)
    }
  }

  const chartData = result?.values.map((v, i) => ({ severity: v, ...result.metrics_by_value[i] })) ?? []
  const tp = result?.tipping_points.business_failures

  return (
    <div className="grid grid-cols-[300px_1fr] gap-3">
      <Panel title="Sweep Configuration">
        <Slider label="Min severity" value={min} onChange={setMin} min={0.05} max={0.45} step={0.05} />
        <Slider label="Max severity" value={max} onChange={setMax} min={0.1} max={1} step={0.05} />
        <Slider label="Steps" value={steps} onChange={setSteps} min={4} max={16} step={1} />
        <Slider label="Days per branch" value={days} onChange={setDays} min={3} max={30} step={1} />
        <button onClick={run} disabled={busy} className="mt-2 w-full rounded-md bg-[var(--accent)] px-3 py-2 text-[12.5px] font-semibold text-[var(--accent-fg)] disabled:opacity-50">
          {busy ? 'Sweeping…' : 'Run Sensitivity Sweep'}
        </button>
      </Panel>

      <Panel title="business_failures vs. drought severity">
        {result ? (
          <>
            <div
              className={`mb-3 rounded-md border-l-4 px-3 py-2 text-[13px] font-semibold ${
                tp ? 'border-l-[var(--danger)] text-[var(--text-primary)]' : 'border-l-[var(--success)] text-[var(--text-tertiary)]'
              }`}
            >
              {tp ? `Tipping point found — severity ${tp.refined_bracket?.[0].toFixed(3)}–${tp.refined_bracket?.[1].toFixed(3)}` : 'No tipping point found — response is smooth.'}
            </div>
            <ChartFrame height={280} csvData={chartData} csvFilename="breaking_point_sweep.csv" pngFilename="breaking_point_sweep.png">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="severity" tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 12 }} />
                  {tp && <ReferenceArea x1={tp.bracket[0]} x2={tp.bracket[1]} fill="var(--danger)" fillOpacity={0.12} />}
                  <Line type="monotone" dataKey="business_failures" stroke="var(--accent)" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </ChartFrame>
          </>
        ) : (
          <div className="text-[12.5px] text-[var(--text-tertiary)]">Run a sweep to see the severity-response curve.</div>
        )}
      </Panel>
    </div>
  )
}

export default function Experiment() {
  const [tab, setTab] = useState<'whatif' | 'breaking' | 'alternate'>('whatif')
  return (
    <div className="flex h-full flex-col">
      <Breadcrumbs items={[{ label: 'Experiment' }]} />
      <div className="flex shrink-0 gap-1 px-6 pt-4">
        {[
          { id: 'whatif', label: 'What If?' },
          { id: 'breaking', label: 'Find the Breaking Point' },
          { id: 'alternate', label: 'Alternate Histories' },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id as typeof tab)}
            className={`rounded-md px-3 py-1.5 text-[12px] font-medium uppercase tracking-wide ${
              tab === t.id ? 'bg-[var(--accent-dim)] text-[var(--accent)]' : 'text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto p-6">
        {tab === 'whatif' ? <WhatIf /> : tab === 'breaking' ? <BreakingPoint /> : <AlternateHistories />}
      </div>
    </div>
  )
}
