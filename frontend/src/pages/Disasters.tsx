import { useState } from 'react'
import { AlertTriangle } from 'lucide-react'
import { Breadcrumbs } from '../components/ui/Breadcrumbs'
import { Panel } from '../components/ui/Panel'
import { useStatus } from '../lib/hooks'
import { api } from '../lib/api'
import { useQueryClient } from '@tanstack/react-query'

const DISASTERS = [
  { id: 'drought', label: 'Drought', endpoint: '/disasters/drought' },
  { id: 'food-shortage', label: 'Food Shortage', endpoint: '/disasters/food-shortage' },
  { id: 'flood', label: 'Flood', endpoint: '/disasters/flood' },
  { id: 'earthquake', label: 'Earthquake', endpoint: '/disasters/earthquake' },
  { id: 'disease-outbreak', label: 'Disease Outbreak', endpoint: '/disasters/disease-outbreak' },
  { id: 'economic-recession', label: 'Economic Recession', endpoint: '/disasters/economic-recession' },
  { id: 'energy-crisis', label: 'Energy Crisis', endpoint: '/disasters/energy-crisis' },
]

export default function Disasters() {
  const { data: status } = useStatus()
  const qc = useQueryClient()
  const [selected, setSelected] = useState(DISASTERS[0])
  const [severity, setSeverity] = useState(0.4)
  const [damageFraction, setDamageFraction] = useState(0.7)
  const [affectedShare, setAffectedShare] = useState(0.3)
  const [result, setResult] = useState<Record<string, unknown> | null>(null)
  const [busy, setBusy] = useState(false)

  const needsSeverity = selected.id === 'drought'
  const needsDamage = selected.id === 'flood' || selected.id === 'earthquake'

  async function trigger() {
    setBusy(true)
    try {
      const payload: Record<string, number> = {}
      if (needsSeverity) payload.severity = severity
      if (needsDamage) {
        payload.damage_fraction = damageFraction
        payload.affected_share = affectedShare
      }
      const res = await api.post<Record<string, unknown>>(selected.endpoint, payload)
      setResult(res)
      await qc.invalidateQueries()
    } catch (e) {
      setResult({ error: String(e) })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex h-full flex-col">
      <Breadcrumbs items={[{ label: 'Disasters' }]} />
      <div className="grid grid-cols-2 gap-3 px-6 py-4">
        <Panel title="Disaster Triggers">
          <div className="mb-3 grid grid-cols-2 gap-1.5">
            {DISASTERS.map((d) => (
              <button
                key={d.id}
                onClick={() => setSelected(d)}
                className={`rounded-md border px-3 py-2 text-left text-[12px] font-medium ${
                  selected.id === d.id
                    ? 'border-[var(--accent)] bg-[var(--accent-dim)] text-[var(--accent)]'
                    : 'border-[var(--border)] text-[var(--text-secondary)] hover:border-[var(--border-strong)]'
                }`}
              >
                {d.label}
              </button>
            ))}
          </div>

          {needsSeverity && (
            <label className="mb-3 block text-[12px]">
              <div className="mb-1 flex justify-between">
                <span className="text-[var(--text-tertiary)] uppercase tracking-wide">Severity</span>
                <span className="font-mono font-semibold">{severity.toFixed(2)}</span>
              </div>
              <input type="range" min={0.1} max={1} step={0.05} value={severity} onChange={(e) => setSeverity(Number(e.target.value))} className="w-full accent-[var(--accent)]" />
            </label>
          )}
          {needsDamage && (
            <>
              <label className="mb-3 block text-[12px]">
                <div className="mb-1 flex justify-between">
                  <span className="text-[var(--text-tertiary)] uppercase tracking-wide">Damage fraction</span>
                  <span className="font-mono font-semibold">{damageFraction.toFixed(2)}</span>
                </div>
                <input type="range" min={0.1} max={1} step={0.05} value={damageFraction} onChange={(e) => setDamageFraction(Number(e.target.value))} className="w-full accent-[var(--accent)]" />
              </label>
              <label className="mb-3 block text-[12px]">
                <div className="mb-1 flex justify-between">
                  <span className="text-[var(--text-tertiary)] uppercase tracking-wide">Affected share</span>
                  <span className="font-mono font-semibold">{affectedShare.toFixed(2)}</span>
                </div>
                <input type="range" min={0.05} max={1} step={0.05} value={affectedShare} onChange={(e) => setAffectedShare(Number(e.target.value))} className="w-full accent-[var(--accent)]" />
              </label>
            </>
          )}

          <button
            onClick={trigger}
            disabled={busy}
            className="flex items-center gap-2 rounded-md bg-[var(--danger)] px-4 py-2 text-[12.5px] font-semibold text-white disabled:opacity-50"
          >
            <AlertTriangle size={14} />
            {busy ? 'Introducing…' : `Introduce ${selected.label}`}
          </button>

          {result && (
            <pre className="animate-fade-in mt-3 overflow-x-auto rounded-md border border-[var(--border)] bg-[var(--bg)] p-3 text-[11px]">
              {JSON.stringify(result, null, 2)}
            </pre>
          )}
        </Panel>

        <Panel title="Active Disasters">
          {status && Object.keys(status.active_disasters_detail).length > 0 ? (
            <div className="space-y-2">
              {Object.entries(status.active_disasters_detail).map(([name, info]) => (
                <div key={name} className="flex items-center justify-between rounded-md border border-[var(--danger)]/30 bg-[var(--danger)]/5 px-3 py-2">
                  <span className="text-[12.5px] font-medium text-[var(--danger)]">{name.replace(/_/g, ' ').toUpperCase()}</span>
                  <span className="font-mono text-[11.5px] text-[var(--text-secondary)]">
                    severity {typeof info.magnitude === 'number' ? info.magnitude.toFixed(2) : '—'}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-[12.5px] text-[var(--text-tertiary)]">No active disasters.</div>
          )}
        </Panel>
      </div>
    </div>
  )
}
