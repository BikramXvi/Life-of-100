import { useEffect, useMemo, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { Breadcrumbs } from '../components/ui/Breadcrumbs'
import { Panel } from '../components/ui/Panel'
import { Drawer, DrawerRow } from '../components/ui/Drawer'
import { ChartFrame } from '../components/ui/ChartFrame'
import { RelationshipGraph } from '../components/people/RelationshipGraph'
import { useCitizens, useCitizenDetail, useHouseholds, useBusinesses } from '../lib/hooks'
import { api } from '../lib/api'
import clsx from 'clsx'
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from 'recharts'

type Scope = 'citizens' | 'households' | 'businesses'

function Bar({ label, pct, color }: { label: string; pct: number; color: string }) {
  return (
    <div className="mb-2.5">
      <div className="mb-1 flex items-center justify-between text-[11px]">
        <span className="uppercase tracking-wide text-[var(--text-tertiary)]">{label}</span>
        <span className="font-mono font-semibold text-[var(--text-primary)]">{Math.round(pct * 100)}%</span>
      </div>
      <div className="h-1.5 rounded-full bg-[var(--border)]">
        <div className="h-full rounded-full" style={{ width: `${pct * 100}%`, background: color }} />
      </div>
    </div>
  )
}

export default function People() {
  const { citizenId: routeCitizenId } = useParams<{ citizenId?: string }>()
  const [params] = useSearchParams()
  const [scope, setScope] = useState<Scope>((params.get('scope') as Scope) || 'citizens')
  const [query, setQuery] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(routeCitizenId ?? params.get('id'))
  const [answer, setAnswer] = useState<string | null>(null)
  const [asking, setAsking] = useState(false)
  const [selectedHousehold, setSelectedHousehold] = useState<string | null>(null)
  const [selectedBusiness, setSelectedBusiness] = useState<string | null>(null)

  // Route param changes (e.g. navigating here again from the command
  // palette while already on /people) don't remount this component, so the
  // initial-state value above only fires once -- sync on every change too.
  useEffect(() => {
    if (routeCitizenId) setSelectedId(routeCitizenId)
  }, [routeCitizenId])

  const { data: citizens } = useCitizens()
  const { data: households } = useHouseholds()
  const { data: businesses } = useBusinesses()

  const filteredCitizens = useMemo(() => {
    if (!citizens) return []
    const q = query.toLowerCase()
    return citizens
      .filter((c) => !q || c.name.toLowerCase().includes(q) || c.citizen_id.includes(q))
      .sort((a, b) => b.age - a.age)
  }, [citizens, query])

  const listSelected = citizens?.find((c) => c.citizen_id === selectedId) ?? filteredCitizens[0]
  // The directory list omits personality/marital_status/education_level/
  // credit_score to stay cheap to poll -- pull those in from the detail
  // endpoint once a citizen is actually selected, and layer them on top.
  const { data: detail } = useCitizenDetail(listSelected?.citizen_id)
  const selected = listSelected ? { ...listSelected, ...detail } : undefined

  async function askHistorian(question: string) {
    if (!selected) return
    setAsking(true)
    setAnswer(null)
    try {
      const res = await api.post<{ answer: string; cited_event_ids: string[]; evidence_considered: number }>(
        '/ai/historian/ask',
        { citizen_id: selected.citizen_id, question },
      )
      setAnswer(`${res.answer}\n\n— ${res.cited_event_ids.length} cited event(s) of ${res.evidence_considered} considered.`)
    } catch (e) {
      setAnswer(String(e))
    } finally {
      setAsking(false)
    }
  }

  return (
    <div className="flex h-full flex-col">
      <Breadcrumbs items={[{ label: 'People' }]} />

      <div className="flex shrink-0 gap-1 px-6 pt-4">
        {(['citizens', 'households', 'businesses'] as Scope[]).map((s) => (
          <button
            key={s}
            onClick={() => setScope(s)}
            className={clsx(
              'rounded-md px-3 py-1.5 text-[12px] font-medium uppercase tracking-wide',
              scope === s ? 'bg-[var(--accent-dim)] text-[var(--accent)]' : 'text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]',
            )}
          >
            {s}
          </button>
        ))}
      </div>

      {scope === 'citizens' && (
        <div className="grid min-h-0 flex-1 grid-cols-[300px_1fr] gap-3 px-6 py-4">
          <Panel title="Directory" padded={false} className="flex min-h-0 flex-col">
            <div className="border-b border-[var(--border)] p-2">
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search name or ID…"
                className="w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-2.5 py-1.5 text-[12.5px] outline-none focus:border-[var(--accent)]"
              />
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto">
              {filteredCitizens.map((c) => (
                <button
                  key={c.citizen_id}
                  onClick={() => setSelectedId(c.citizen_id)}
                  className={clsx(
                    'flex w-full items-center justify-between px-3 py-2 text-left text-[12.5px] border-b border-[var(--border)]',
                    selected?.citizen_id === c.citizen_id ? 'bg-[var(--accent-dim)]' : 'hover:bg-[var(--surface-hover)]',
                  )}
                >
                  <span className={selected?.citizen_id === c.citizen_id ? 'text-[var(--accent)] font-medium' : 'text-[var(--text-secondary)]'}>
                    {c.name}
                  </span>
                  <span className="font-mono text-[10.5px] text-[var(--text-tertiary)]">{c.citizen_id}</span>
                </button>
              ))}
            </div>
          </Panel>

          <div className="min-h-0 overflow-y-auto pr-1">
            {selected ? (
              <div className="flex flex-col gap-3">
                <Panel>
                  <div className="mb-1 text-[10.5px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
                    Citizen {selected.citizen_id}
                  </div>
                  <div className="mb-2 font-mono text-[24px] font-bold">{selected.name}</div>
                  <div className="flex flex-wrap gap-1.5">
                    <span className={clsx('rounded border px-2 py-0.5 text-[10.5px] font-medium', selected.alive ? 'border-[var(--success)] text-[var(--success)]' : 'border-[var(--danger)] text-[var(--danger)]')}>
                      {selected.alive ? 'ALIVE' : 'DECEASED'}
                    </span>
                    <span className="rounded border border-[var(--border)] px-2 py-0.5 text-[10.5px] text-[var(--text-secondary)]">AGE {selected.age}</span>
                    <span className="rounded border border-[var(--border)] px-2 py-0.5 text-[10.5px] text-[var(--text-secondary)]">{selected.occupation.toUpperCase()}</span>
                    <span className="rounded border border-[var(--border)] px-2 py-0.5 text-[10.5px] text-[var(--text-secondary)]">HH {selected.household_id}</span>
                  </div>
                </Panel>

                <div className="grid grid-cols-2 gap-3">
                  <Panel title="Identity & Employment">
                    <div className="space-y-1.5 text-[12.5px]">
                      <div className="flex justify-between border-b border-[var(--border)] py-1.5">
                        <span className="text-[var(--text-tertiary)]">Gender</span>
                        <span>{selected.gender}</span>
                      </div>
                      <div className="flex justify-between border-b border-[var(--border)] py-1.5">
                        <span className="text-[var(--text-tertiary)]">Marital status</span>
                        <span>{selected.marital_status ?? '—'}</span>
                      </div>
                      <div className="flex justify-between border-b border-[var(--border)] py-1.5">
                        <span className="text-[var(--text-tertiary)]">Education</span>
                        <span>{selected.education_level ?? '—'}</span>
                      </div>
                      <div className="flex justify-between py-1.5">
                        <span className="text-[var(--text-tertiary)]">Employer</span>
                        <span className="font-mono">{selected.employer_id ?? 'none'}</span>
                      </div>
                    </div>
                  </Panel>

                  <Panel title="Psychology">
                    <Bar label="Stress" pct={selected.stress} color="var(--danger)" />
                    {selected.personality && (
                      <ChartFrame
                        height={170}
                        csvData={[{ citizen_id: selected.citizen_id, ...selected.personality }]}
                        csvFilename={`${selected.citizen_id}_personality.csv`}
                        pngFilename={`${selected.citizen_id}_personality.png`}
                      >
                        <ResponsiveContainer width="100%" height="100%">
                          <RadarChart
                            data={[
                              { trait: 'Risk tolerance', value: selected.personality.risk_tolerance * 100 },
                              { trait: 'Ambition', value: selected.personality.ambition * 100 },
                              { trait: 'Patience', value: selected.personality.patience * 100 },
                              { trait: 'Social', value: selected.personality.social_tendency * 100 },
                            ]}
                          >
                            <PolarGrid stroke="var(--border)" />
                            <PolarAngleAxis dataKey="trait" tick={{ fontSize: 9.5, fill: 'var(--text-tertiary)' }} />
                            <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
                            <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 12 }} />
                            <Radar dataKey="value" stroke="var(--accent)" fill="var(--accent)" fillOpacity={0.25} isAnimationActive={false} />
                          </RadarChart>
                        </ResponsiveContainer>
                      </ChartFrame>
                    )}
                  </Panel>

                  <Panel title="Finances">
                    <div className="space-y-1.5 text-[12.5px]">
                      <div className="flex justify-between border-b border-[var(--border)] py-1.5">
                        <span className="text-[var(--text-tertiary)]">Savings</span>
                        <span className="font-mono tabular-nums">{selected.savings.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between border-b border-[var(--border)] py-1.5">
                        <span className="text-[var(--text-tertiary)]">Debt</span>
                        <span className="font-mono tabular-nums">{selected.debt.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between py-1.5">
                        <span className="text-[var(--text-tertiary)]">Salary</span>
                        <span className="font-mono tabular-nums">{selected.salary.toLocaleString()}</span>
                      </div>
                    </div>
                  </Panel>

                  <Panel title="Health">
                    <Bar label="Health score" pct={selected.health_score} color="var(--success)" />
                    <div className="mt-2 flex justify-between text-[12.5px]">
                      <span className="text-[var(--text-tertiary)]">Credit score</span>
                      <span className="font-mono">{selected.credit_score ?? '—'}</span>
                    </div>
                  </Panel>
                </div>

                <Panel title="Historian Agent" subtitle="Grounded in real events — never a fabricated citation">
                  <button
                    onClick={() => askHistorian('Tell this citizen\'s story so far — what has happened to them and why?')}
                    disabled={asking}
                    className="rounded-md border border-[var(--border-strong)] px-3 py-1.5 text-[12.5px] font-medium text-[var(--accent)] hover:bg-[var(--accent-dim)] disabled:opacity-50"
                  >
                    {asking ? 'Asking…' : 'Explain my story'}
                  </button>
                  {answer && (
                    <div className="animate-fade-in mt-3 whitespace-pre-line rounded-md border border-[var(--border)] bg-[var(--bg)] p-3 text-[12.5px] leading-relaxed">
                      {answer}
                    </div>
                  )}
                </Panel>

                <Panel title="Relationship Network" subtitle="Family, friend, coworker, and neighbor ties — click a node to jump to them">
                  <RelationshipGraph citizenId={selected.citizen_id} citizenName={selected.name} onSelect={(id) => setSelectedId(id)} />
                </Panel>
              </div>
            ) : (
              <div className="p-6 text-[13px] text-[var(--text-tertiary)]">Select a citizen from the directory.</div>
            )}
          </div>
        </div>
      )}

      {scope === 'households' && (
        <div className="flex-1 overflow-y-auto px-6 py-4">
          <Panel title="Household Registry" padded={false}>
            <div className="overflow-x-auto">
              <table className="w-full text-[12.5px]">
                <thead>
                  <tr className="border-b border-[var(--border)] text-left text-[10.5px] uppercase tracking-wide text-[var(--text-tertiary)]">
                    <th className="px-3 py-2">ID</th>
                    <th className="px-3 py-2">Members</th>
                    <th className="px-3 py-2">Savings</th>
                    <th className="px-3 py-2">Debt</th>
                    <th className="px-3 py-2">Stress</th>
                  </tr>
                </thead>
                <tbody>
                  {(households ?? []).map((h) => (
                    <tr
                      key={h.household_id}
                      onClick={() => setSelectedHousehold(h.household_id)}
                      className="cursor-pointer border-b border-[var(--border)] hover:bg-[var(--surface-hover)]"
                    >
                      <td className="px-3 py-2 font-mono">{h.household_id}</td>
                      <td className="px-3 py-2 tabular-nums">{h.member_ids.length}</td>
                      <td className="px-3 py-2 tabular-nums">{h.savings.toLocaleString()}</td>
                      <td className="px-3 py-2 tabular-nums">{h.debt.toLocaleString()}</td>
                      <td className="px-3 py-2 tabular-nums">{(h.financial_stress * 100).toFixed(0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </div>
      )}

      {scope === 'businesses' && (
        <div className="flex-1 overflow-y-auto px-6 py-4">
          <Panel title="Business Registry" padded={false}>
            <div className="overflow-x-auto">
              <table className="w-full text-[12.5px]">
                <thead>
                  <tr className="border-b border-[var(--border)] text-left text-[10.5px] uppercase tracking-wide text-[var(--text-tertiary)]">
                    <th className="px-3 py-2">ID</th>
                    <th className="px-3 py-2">Industry</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2">Cash</th>
                    <th className="px-3 py-2">Employees</th>
                  </tr>
                </thead>
                <tbody>
                  {(businesses ?? []).map((b) => (
                    <tr
                      key={b.business_id}
                      onClick={() => setSelectedBusiness(b.business_id)}
                      className="cursor-pointer border-b border-[var(--border)] hover:bg-[var(--surface-hover)]"
                    >
                      <td className="px-3 py-2 font-mono">{b.business_id}</td>
                      <td className="px-3 py-2">{b.industry.replace(/_/g, ' ')}</td>
                      <td className="px-3 py-2">
                        <span className={b.active ? 'text-[var(--success)]' : 'text-[var(--danger)]'}>{b.active ? 'ACTIVE' : 'FAILED'}</span>
                      </td>
                      <td className="px-3 py-2 tabular-nums">{b.cash.toLocaleString()}</td>
                      <td className="px-3 py-2 tabular-nums">{b.headcount}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </div>
      )}

      <Drawer
        open={!!selectedHousehold}
        onClose={() => setSelectedHousehold(null)}
        title={selectedHousehold ?? ''}
        subtitle="Household"
      >
        {(() => {
          const hh = households?.find((h) => h.household_id === selectedHousehold)
          if (!hh) return null
          const members = (citizens ?? []).filter((c) => hh.member_ids.includes(c.citizen_id))
          return (
            <div>
              <DrawerRow label="Members" value={hh.member_ids.length} />
              <DrawerRow label="Property value" value={hh.property_value.toLocaleString()} />
              <DrawerRow label="Income" value={hh.income.toLocaleString()} />
              <DrawerRow label="Expenses" value={hh.expenses.toLocaleString()} />
              <DrawerRow label="Savings" value={hh.savings.toLocaleString()} />
              <DrawerRow label="Debt" value={hh.debt.toLocaleString()} />
              <DrawerRow label="Financial stress" value={`${(hh.financial_stress * 100).toFixed(0)}%`} />
              <div className="mt-4 mb-2 text-[10.5px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">Members</div>
              {members.map((m) => (
                <button
                  key={m.citizen_id}
                  onClick={() => {
                    setScope('citizens')
                    setSelectedId(m.citizen_id)
                    setSelectedHousehold(null)
                  }}
                  className="flex w-full items-center justify-between border-b border-[var(--border)] py-2 text-left text-[12.5px] hover:text-[var(--accent)]"
                >
                  <span>{m.name}</span>
                  <span className="text-[11px] text-[var(--text-tertiary)]">{m.occupation}</span>
                </button>
              ))}
            </div>
          )
        })()}
      </Drawer>

      <Drawer
        open={!!selectedBusiness}
        onClose={() => setSelectedBusiness(null)}
        title={selectedBusiness ?? ''}
        subtitle="Business"
      >
        {(() => {
          const biz = businesses?.find((b) => b.business_id === selectedBusiness)
          if (!biz) return null
          const employees = (citizens ?? []).filter((c) => biz.employee_ids.includes(c.citizen_id))
          return (
            <div>
              <DrawerRow label="Industry" value={biz.industry.replace(/_/g, ' ')} />
              <DrawerRow label="Status" value={biz.active ? 'Active' : 'Failed'} />
              <DrawerRow label="Cash" value={biz.cash.toLocaleString()} />
              <DrawerRow label="Revenue" value={biz.revenue.toLocaleString()} />
              <DrawerRow label="Expenses" value={biz.expenses.toLocaleString()} />
              <DrawerRow label="Profit" value={biz.profit.toLocaleString()} />
              <div className="mt-4 mb-2 text-[10.5px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
                Employees ({employees.length})
              </div>
              {employees.map((m) => (
                <button
                  key={m.citizen_id}
                  onClick={() => {
                    setScope('citizens')
                    setSelectedId(m.citizen_id)
                    setSelectedBusiness(null)
                  }}
                  className="flex w-full items-center justify-between border-b border-[var(--border)] py-2 text-left text-[12.5px] hover:text-[var(--accent)]"
                >
                  <span>{m.name}</span>
                  <span className="text-[11px] text-[var(--text-tertiary)]">{m.salary.toLocaleString()}</span>
                </button>
              ))}
            </div>
          )
        })()}
      </Drawer>
    </div>
  )
}
