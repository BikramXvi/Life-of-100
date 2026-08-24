import { useMemo } from 'react'
import { Breadcrumbs } from '../components/ui/Breadcrumbs'
import { Panel } from '../components/ui/Panel'
import { Kpi } from '../components/ui/Kpi'
import { ChartFrame } from '../components/ui/ChartFrame'
import { useCitizens, useBusinesses, useStatus } from '../lib/hooks'
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
  CartesianGrid,
  Treemap,
  Sankey,
} from 'recharts'
import type { TreemapNode, SankeyNodeProps } from 'recharts'

const INDUSTRY_PALETTE = ['var(--accent)', 'var(--teal)', 'var(--violet)', 'var(--warning)', 'var(--success)', 'var(--danger)']

function TreemapCell(props: TreemapNode) {
  const { x, y, width, height, depth, name, active } = props as TreemapNode & { active?: boolean }
  if (depth === 0) return null
  const isLeaf = depth === 2
  const color = INDUSTRY_PALETTE[(props.index ?? 0) % INDUSTRY_PALETTE.length]
  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        style={{
          fill: isLeaf ? color : 'var(--bg-elevated)',
          fillOpacity: isLeaf ? (active === false ? 0.25 : 0.75) : 1,
          stroke: 'var(--border)',
          strokeWidth: 1,
        }}
      />
      {width > 46 && height > 16 && (
        <text
          x={x + 4}
          y={y + 13}
          fontSize={depth === 1 ? 10.5 : 9.5}
          fontWeight={depth === 1 ? 700 : 500}
          style={{ fill: depth === 1 ? 'var(--text-primary)' : 'var(--text-secondary)' }}
        >
          {String(name).slice(0, Math.floor(width / 6))}
        </text>
      )}
    </g>
  )
}

// recharts' default Sankey node label defaults to a dark grey fill that's
// invisible against this app's dark theme -- draw the rect and label
// ourselves so industry/Expenses/Profit names are actually legible.
function SankeyNodeShape({ x, y, width, height, payload }: SankeyNodeProps) {
  const isSink = payload.name === 'Expenses' || payload.name === 'Profit'
  return (
    <g>
      <rect x={x} y={y} width={width} height={height} style={{ fill: 'var(--accent)', fillOpacity: 0.85, stroke: 'var(--border)' }} />
      <text
        x={isSink ? x - 6 : x + width + 6}
        y={y + height / 2}
        dy={4}
        textAnchor={isSink ? 'end' : 'start'}
        fontSize={10.5}
        style={{ fill: 'var(--text-secondary)' }}
      >
        {payload.name}
      </text>
    </g>
  )
}

function median(values: number[]): number {
  if (!values.length) return 0
  const s = [...values].sort((a, b) => a - b)
  const mid = Math.floor(s.length / 2)
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2
}

export default function Analytics() {
  const { data: status } = useStatus()
  const { data: citizens } = useCitizens()
  const { data: businesses } = useBusinesses()

  const wealth = useMemo(() => (citizens ?? []).filter((c) => c.alive).map((c) => c.savings - c.debt), [citizens])

  const lorenz = useMemo(() => {
    if (!wealth.length) return []
    const sorted = [...wealth].sort((a, b) => a - b)
    const shifted = sorted.map((w) => w - Math.min(0, sorted[0])) // shift so no negatives skew the curve
    const total = shifted.reduce((a, b) => a + b, 0) || 1
    let cum = 0
    const points = [{ pop: 0, wealth: 0 }]
    sorted.forEach((_, i) => {
      cum += shifted[i]
      points.push({ pop: Math.round(((i + 1) / sorted.length) * 100), wealth: Math.round((cum / total) * 100) })
    })
    return points
  }, [wealth])

  const histogram = useMemo(() => {
    if (!wealth.length) return []
    const min = Math.min(...wealth)
    const max = Math.max(...wealth)
    const bins = 16
    const width = (max - min) / bins || 1
    const buckets = Array.from({ length: bins }, (_, i) => ({ range: Math.round(min + i * width), count: 0 }))
    for (const w of wealth) {
      const idx = Math.min(bins - 1, Math.floor((w - min) / width))
      buckets[idx].count++
    }
    return buckets
  }, [wealth])

  const industryActivity = useMemo(() => {
    const map = new Map<string, { industry: string; cash: number; count: number }>()
    for (const b of businesses ?? []) {
      const entry = map.get(b.industry) ?? { industry: b.industry, cash: 0, count: 0 }
      entry.cash += b.cash
      entry.count += 1
      map.set(b.industry, entry)
    }
    return Array.from(map.values())
  }, [businesses])

  // Business size map: two-level treemap, industry -> individual business,
  // sized by cash on hand (a real recorded balance, not a derived estimate).
  const treemapData = useMemo(() => {
    const byIndustry = new Map<string, { name: string; children: { name: string; size: number; active: boolean }[] }>()
    for (const b of businesses ?? []) {
      const entry = byIndustry.get(b.industry) ?? { name: b.industry.replace(/_/g, ' '), children: [] }
      entry.children.push({ name: b.business_id, size: Math.max(1, b.cash), active: b.active })
      byIndustry.set(b.industry, entry)
    }
    return Array.from(byIndustry.values())
  }, [businesses])

  // Money flow: each industry's aggregate revenue split into what it spent
  // vs. what it kept as profit -- both real recorded per-business fields,
  // summed. Losses (negative aggregate profit) are clipped to 0 for the flow
  // since Sankey values can't be negative; the KPI strip covers failures.
  const sankeyData = useMemo(() => {
    const byIndustry = new Map<string, { expenses: number; profit: number }>()
    for (const b of businesses ?? []) {
      const entry = byIndustry.get(b.industry) ?? { expenses: 0, profit: 0 }
      entry.expenses += Math.max(0, b.expenses)
      entry.profit += Math.max(0, b.profit)
      byIndustry.set(b.industry, entry)
    }
    const industries = Array.from(byIndustry.keys())
    const nodes = [
      ...industries.map((i) => ({ name: i.replace(/_/g, ' ') })),
      { name: 'Expenses' },
      { name: 'Profit' },
    ]
    const expensesIdx = industries.length
    const profitIdx = industries.length + 1
    const links = industries.flatMap((industry, i) => {
      const { expenses, profit } = byIndustry.get(industry)!
      const out = []
      if (expenses > 0) out.push({ source: i, target: expensesIdx, value: expenses })
      if (profit > 0) out.push({ source: i, target: profitIdx, value: profit })
      return out
    })
    return { nodes, links }
  }, [businesses])

  const businessSizeCsv = useMemo(
    () => (businesses ?? []).map((b) => ({ industry: b.industry, business_id: b.business_id, cash: b.cash, active: b.active })),
    [businesses],
  )

  const moneyFlowCsv = useMemo(() => {
    const map = new Map<string, { industry: string; expenses: number; profit: number }>()
    for (const b of businesses ?? []) {
      const entry = map.get(b.industry) ?? { industry: b.industry, expenses: 0, profit: 0 }
      entry.expenses += Math.max(0, b.expenses)
      entry.profit += Math.max(0, b.profit)
      map.set(b.industry, entry)
    }
    return Array.from(map.values())
  }, [businesses])

  const totalWealth = wealth.reduce((a, b) => a + b, 0)
  const medianWealth = median(wealth)
  const failedBusinesses = (businesses ?? []).filter((b) => !b.active).length

  return (
    <div className="flex h-full flex-col">
      <Breadcrumbs items={[{ label: 'Analytics' }]} />
      <div className="flex flex-col gap-3 px-6 py-4">
        <div className="grid grid-cols-4 gap-3">
          <Kpi label="Total Wealth" value={`NPR ${(totalWealth / 1e6).toFixed(2)}M`} />
          <Kpi label="Median Wealth" value={medianWealth.toLocaleString()} />
          <Kpi label="Food Price Index" value={status ? status.food_price_index.toFixed(2) : '—'} color="var(--warning)" />
          <Kpi label="Business Failures" value={String(failedBusinesses)} color="var(--danger)" />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Panel title="Wealth Distribution" subtitle="Net worth (savings − debt), all living citizens">
            <ChartFrame csvData={histogram} csvFilename="wealth_distribution.csv" pngFilename="wealth_distribution.png">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={histogram}>
                  <CartesianGrid stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="range" tick={{ fontSize: 9, fill: 'var(--text-tertiary)' }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 12 }} />
                  <Bar dataKey="count" fill="var(--teal)" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartFrame>
          </Panel>

          <Panel title="Lorenz Curve" subtitle="Cumulative wealth share vs. cumulative population share">
            <ChartFrame csvData={lorenz} csvFilename="lorenz_curve.csv" pngFilename="lorenz_curve.png">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={lorenz}>
                  <CartesianGrid stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="pop" tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} unit="%" />
                  <YAxis tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }} axisLine={false} tickLine={false} unit="%" />
                  <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 12 }} />
                  <Area type="monotone" dataKey="wealth" stroke="var(--accent)" fill="var(--accent)" fillOpacity={0.15} strokeWidth={2} isAnimationActive={false} />
                  <Line type="linear" data={[{ pop: 0, wealth: 0 }, { pop: 100, wealth: 100 }]} dataKey="wealth" stroke="var(--text-tertiary)" strokeDasharray="4 4" dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </ChartFrame>
          </Panel>

          <Panel title="Business Activity by Industry" className="col-span-2">
            <ChartFrame csvData={industryActivity} csvFilename="industry_activity.csv" pngFilename="industry_activity.png">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={industryActivity}>
                  <CartesianGrid stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="industry" tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }} axisLine={{ stroke: 'var(--border)' }} tickLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 12 }} />
                  <Bar dataKey="cash" fill="var(--violet)" radius={[2, 2, 0, 0]} name="Total cash" />
                </BarChart>
              </ResponsiveContainer>
            </ChartFrame>
          </Panel>

          <Panel title="Business Size Map" subtitle="Industry → business, sized by cash on hand. Dim = inactive." className="col-span-2">
            <ChartFrame height={280} csvData={businessSizeCsv} csvFilename="business_size_map.csv" pngFilename="business_size_map.png">
              <ResponsiveContainer width="100%" height="100%">
                <Treemap data={treemapData} dataKey="size" stroke="var(--border)" content={(props) => <TreemapCell {...(props as TreemapNode)} />} isAnimationActive={false} />
              </ResponsiveContainer>
            </ChartFrame>
          </Panel>

          <Panel title="Money Flow by Industry" subtitle="Aggregate revenue split into expenses vs. profit kept, per industry (losses excluded from the flow)" className="col-span-2">
            <ChartFrame height={260} csvData={moneyFlowCsv} csvFilename="money_flow.csv" pngFilename="money_flow.png">
              <ResponsiveContainer width="100%" height="100%">
                <Sankey
                  data={sankeyData}
                  nodePadding={22}
                  nodeWidth={12}
                  linkCurvature={0.5}
                  node={(props) => <SankeyNodeShape {...(props as SankeyNodeProps)} />}
                  link={{ stroke: 'var(--accent)', strokeOpacity: 0.18 } as any}
                  margin={{ top: 8, right: 70, bottom: 8, left: 110 }}
                >
                  <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 12 }} />
                </Sankey>
              </ResponsiveContainer>
            </ChartFrame>
          </Panel>
        </div>
      </div>
    </div>
  )
}
