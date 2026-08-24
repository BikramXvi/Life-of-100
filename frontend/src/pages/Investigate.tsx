import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { Breadcrumbs } from '../components/ui/Breadcrumbs'
import { Panel } from '../components/ui/Panel'
import { CausalGraph } from '../components/investigate/CausalGraph'
import { useEvents } from '../lib/hooks'
import { api } from '../lib/api'
import type { SimEvent } from '../lib/types'

const CAUSE_KEYS = new Set(['caused_by', 'caused_by_disaster_event_id', 'proposed_event_id'])

export default function Investigate() {
  // A larger pull than most pages -- the causal graph is built entirely
  // client-side from the full log (see CausalGraph.tsx), not one API call
  // per node, so it needs real breadth to find multi-level branches.
  const { data: events } = useEvents(3000)
  const [params] = useSearchParams()
  const qc = useQueryClient()
  const [eventId, setEventId] = useState('')
  const [tracedId, setTracedId] = useState<string | null>(null)
  const [effects, setEffects] = useState<SimEvent[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pendingSim, setPendingSim] = useState<string | null>(null)
  const [activating, setActivating] = useState(false)

  // Cross-linked from elsewhere (e.g. Alternate Histories' divergent-event
  // list) via /investigate?trace=<event_id>&sim=<owning_simulation_id> --
  // auto-trigger the trace once. The sim hint lets the 404 case below offer
  // a one-click fix instead of a dead end.
  useEffect(() => {
    const id = params.get('trace')
    if (id) trace(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params])

  async function trace(id: string) {
    if (!id) return
    setLoading(true)
    setError(null)
    setPendingSim(null)
    try {
      const e = await api.get<SimEvent[]>(`/events/${id}/effects`)
      setEffects(e)
      setTracedId(id)
      setEventId(id)
    } catch (err) {
      setEffects(null)
      setTracedId(null)
      // Error objects stringify with an "Error: " prefix ahead of api.ts's
      // own "<status> <path>: <body>" message -- read .message directly so
      // the startsWith('404') check below actually matches.
      const msg = err instanceof Error ? err.message : String(err)
      const ownerSim = params.get('sim')
      // /events/{id}/effects only looks at the currently-active simulation --
      // an event deep-linked in from a different (inactive) timeline 404s.
      if (msg.startsWith('404') && ownerSim) {
        setError(`This event belongs to timeline "${ownerSim}", which isn't the active one.`)
        setPendingSim(ownerSim)
      } else {
        setError(msg)
      }
    } finally {
      setLoading(false)
    }
  }

  async function activateAndRetry(id: string) {
    if (!pendingSim) return
    setActivating(true)
    try {
      await api.post(`/simulation/activate/${pendingSim}`)
      await qc.invalidateQueries()
      await trace(id)
    } finally {
      setActivating(false)
    }
  }

  const tracedEvent = events?.find((e) => e.event_id === tracedId)

  return (
    <div className="flex h-full flex-col">
      <Breadcrumbs items={[{ label: 'Investigate' }]} />
      <div className="grid min-h-0 flex-1 grid-cols-[1.6fr_1fr] gap-3 px-6 py-4">
        <Panel
          title="Causal Graph // Trace"
          subtitle="Every arrow is a real, recorded caused_by link — never inferred. Click any node to re-root the trace there."
          className="min-w-0"
        >
          {error && (
            <div className="mb-3 flex items-center justify-between gap-3 rounded-md border-l-4 border-[var(--warning)] bg-[var(--bg)] px-3 py-2 text-[12px] text-[var(--text-secondary)]">
              <span>{error}</span>
              {pendingSim && (
                <button
                  onClick={() => activateAndRetry(params.get('trace') || eventId)}
                  disabled={activating}
                  className="shrink-0 rounded border border-[var(--border-strong)] px-2 py-1 text-[11px] font-medium text-[var(--accent)] hover:bg-[var(--accent-dim)] disabled:opacity-50"
                >
                  {activating ? 'Activating…' : 'Activate & retrace'}
                </button>
              )}
            </div>
          )}
          <div className="mb-3 flex gap-2">
            <input
              value={eventId}
              onChange={(e) => setEventId(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && trace(eventId)}
              placeholder="event_id…"
              className="flex-1 rounded-md border border-[var(--border)] bg-[var(--bg)] px-2.5 py-1.5 font-mono text-[12px] outline-none focus:border-[var(--accent)]"
            />
            <button
              onClick={() => trace(eventId)}
              disabled={loading || !eventId}
              className="rounded-md bg-[var(--accent)] px-3 py-1.5 text-[12.5px] font-semibold text-[var(--accent-fg)] disabled:opacity-50"
            >
              {loading ? 'Tracing…' : 'Trace'}
            </button>
          </div>

          <div className="max-h-[560px] overflow-y-auto">
            {!tracedId && <div className="text-[12.5px] text-[var(--text-tertiary)]">Enter an event_id, or pick one from Recent Events below.</div>}
            {tracedId && events && <CausalGraph events={events} targetId={tracedId} onSelectEvent={trace} />}
          </div>
        </Panel>

        <Panel title="Event Detail Inspector" className="min-w-0">
          {tracedEvent ? (
            <div className="text-[12.5px]">
              <div className="mb-3 inline-block rounded border border-[var(--accent)] px-2 py-0.5 font-mono text-[11px] text-[var(--accent)]">
                ID: {tracedEvent.event_id}
              </div>
              <div className="mb-3 space-y-1">
                <div className="flex justify-between border-b border-[var(--border)] py-1">
                  <span className="text-[var(--text-tertiary)]">Type</span>
                  <span>{tracedEvent.event_type}</span>
                </div>
                <div className="flex justify-between border-b border-[var(--border)] py-1">
                  <span className="text-[var(--text-tertiary)]">Entity</span>
                  <span className="font-mono">{tracedEvent.source_entity}</span>
                </div>
                <div className="flex justify-between border-b border-[var(--border)] py-1">
                  <span className="text-[var(--text-tertiary)]">Day</span>
                  <span>{Math.floor(tracedEvent.simulation_tick / 24)}</span>
                </div>
              </div>
              <div className="mb-1.5 text-[10.5px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">Payload</div>
              <pre className="mb-4 overflow-x-auto rounded-md border border-[var(--border)] bg-[var(--bg)] p-2 text-[10.5px]">
                {JSON.stringify(
                  Object.fromEntries(Object.entries(tracedEvent.payload).filter(([k]) => !CAUSE_KEYS.has(k))),
                  null,
                  2,
                )}
              </pre>
              <div className="mb-1.5 text-[10.5px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">Downstream (direct effects)</div>
              <div className={effects && effects.length > 0 ? 'text-[var(--danger)]' : 'text-[var(--text-tertiary)]'}>
                {effects?.length ?? 0} event(s) directly caused by this one, touching{' '}
                {new Set((effects ?? []).map((e) => e.source_entity)).size} entit(y/ies).
              </div>
              <div className="mt-3 max-h-[280px] overflow-y-auto">
                {(effects ?? []).map((e) => (
                  <button
                    key={e.event_id}
                    onClick={() => trace(e.event_id)}
                    className="flex w-full items-center justify-between border-b border-[var(--border)] py-1.5 text-left font-mono text-[11.5px] hover:text-[var(--accent)]"
                  >
                    <span>D{Math.floor(e.simulation_tick / 24)} · {e.event_type}</span>
                    <span className="text-[var(--text-tertiary)]">{e.source_entity}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-[12.5px] text-[var(--text-tertiary)]">Trace an event to inspect it here.</div>
          )}
        </Panel>
      </div>

      <Panel title="Recent Events" className="mx-6 mb-4" padded={false}>
        <div className="max-h-[180px] overflow-y-auto">
          {(events ?? []).slice(0, 30).map((e) => (
            <div
              key={e.event_id}
              onClick={() => trace(e.event_id)}
              className="flex cursor-pointer items-center justify-between border-b border-[var(--border)] px-3 py-1.5 font-mono text-[11px] hover:bg-[var(--surface-hover)]"
            >
              <span className="text-[var(--text-secondary)]">
                D{Math.floor(e.simulation_tick / 24)} · {e.event_type}
              </span>
              <span className="text-[var(--text-tertiary)]">{e.event_id}</span>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  )
}
