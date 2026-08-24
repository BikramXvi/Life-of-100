import { useState } from 'react'
import { ArrowRight } from 'lucide-react'
import { Breadcrumbs } from '../components/ui/Breadcrumbs'
import { Panel } from '../components/ui/Panel'
import { useStatus, useCitizens, useBusinesses } from '../lib/hooks'
import { api } from '../lib/api'

function Pipeline() {
  const steps = ['Propose', 'Validate', 'Accept / Reject', 'Apply']
  return (
    <div className="mb-4 flex items-center gap-1.5 rounded-md border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-[11.5px]">
      {steps.map((s, i) => (
        <span key={s} className="flex items-center gap-1.5">
          <span className="text-[var(--text-secondary)]">{s}</span>
          {i < steps.length - 1 && <ArrowRight size={12} className="text-[var(--text-tertiary)]" />}
        </span>
      ))}
    </div>
  )
}

function ResultBox({ result }: { result: unknown }) {
  if (!result) return null
  return (
    <pre className="animate-fade-in mt-3 overflow-x-auto rounded-md border border-[var(--border)] bg-[var(--bg)] p-3 text-[11px]">
      {JSON.stringify(result, null, 2)}
    </pre>
  )
}

export default function AiAgents() {
  const { data: status } = useStatus()
  const { data: citizens } = useCitizens()
  const { data: businesses } = useBusinesses()

  const [citizenId, setCitizenId] = useState('')
  const [question, setQuestion] = useState("Why did this citizen's situation change?")
  const [historianResult, setHistorianResult] = useState<unknown>(null)
  const [householdResult, setHouseholdResult] = useState<unknown>(null)
  const [govResult, setGovResult] = useState<unknown>(null)
  const [bizId, setBizId] = useState('')
  const [bizResult, setBizResult] = useState<unknown>(null);

  return (
    <div className="flex h-full flex-col">
      <Breadcrumbs items={[{ label: 'AI Agents' }]} />
      <div className="px-6 py-4">
        <div className="mb-4 rounded-md border border-[var(--warning)]/30 bg-[var(--warning)]/5 px-3 py-2 text-[12px] text-[var(--text-secondary)]">
          These agents never touch the city directly. Every proposal passes <b>propose → validate → accept/reject → apply</b>,
          each step its own logged event. An agent suggesting something out of bounds is rejected, not silently clamped.
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Panel title="Historian Agent" subtitle="Grounded in real events, never fabricated citations">
            <Pipeline />
            <select
              value={citizenId}
              onChange={(e) => setCitizenId(e.target.value)}
              className="mb-2 w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-2.5 py-1.5 text-[12px]"
            >
              <option value="">Select citizen…</option>
              {(citizens ?? []).map((c) => (
                <option key={c.citizen_id} value={c.citizen_id}>{c.name} ({c.citizen_id})</option>
              ))}
            </select>
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              className="mb-2 w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-2.5 py-1.5 text-[12px]"
            />
            <button
              disabled={!citizenId}
              onClick={async () => setHistorianResult(await api.post('/ai/historian/ask', { citizen_id: citizenId, question }))}
              className="rounded-md border border-[var(--border-strong)] px-3 py-1.5 text-[12px] font-medium text-[var(--accent)] hover:bg-[var(--accent-dim)] disabled:opacity-40"
            >
              Ask Historian
            </button>
            <ResultBox result={historianResult} />
          </Panel>

          <Panel title="Government Agent" subtitle={status ? `Sees food price ${status.food_price_index.toFixed(2)}, disasters: ${status.active_disasters.join(', ') || 'none'}` : ''}>
            <Pipeline />
            <button
              onClick={async () => setGovResult(await api.post('/ai/government/propose'))}
              className="rounded-md border border-[var(--border-strong)] px-3 py-1.5 text-[12px] font-medium text-[var(--accent)] hover:bg-[var(--accent-dim)]"
            >
              Propose Policy
            </button>
            <ResultBox result={govResult} />
          </Panel>

          <Panel title="Household Decision Agent" subtitle="Proposes, never decides unilaterally">
            <Pipeline />
            <button
              disabled={!citizenId}
              onClick={async () =>
                setHouseholdResult(
                  await api.post('/ai/household/propose', { citizen_id: citizenId, decision_context: 'considering a major loan' }),
                )
              }
              className="rounded-md border border-[var(--border-strong)] px-3 py-1.5 text-[12px] font-medium text-[var(--accent)] hover:bg-[var(--accent-dim)] disabled:opacity-40"
            >
              Ask Household Agent (uses selected citizen)
            </button>
            <ResultBox result={householdResult} />
          </Panel>

          <Panel title="Business Agent" subtitle="Proposes hire/fire/loan actions, bounded by validator.py">
            <Pipeline />
            <select value={bizId} onChange={(e) => setBizId(e.target.value)} className="mb-2 w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-2.5 py-1.5 text-[12px]">
              <option value="">Select business…</option>
              {(businesses ?? []).map((b) => (
                <option key={b.business_id} value={b.business_id}>{b.business_id} — {b.industry}</option>
              ))}
            </select>
            <button
              disabled={!bizId}
              onClick={async () => setBizResult(await api.post(`/ai/business/${bizId}/propose`))}
              className="rounded-md border border-[var(--border-strong)] px-3 py-1.5 text-[12px] font-medium text-[var(--accent)] hover:bg-[var(--accent-dim)] disabled:opacity-40"
            >
              Propose Business Action
            </button>
            <ResultBox result={bizResult} />
          </Panel>
        </div>
      </div>
    </div>
  )
}
