import { useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Breadcrumbs } from '../components/ui/Breadcrumbs'
import { Panel } from '../components/ui/Panel'
import { useCitizens, useHouseholds, useBusinesses, useEvents } from '../lib/hooks'

const RESULT_CAP = 40

function SectionHeading({ label, shown, total }: { label: string; shown: number; total: number }) {
  return (
    <span>
      {label}
      {total > 0 && (
        <span className="ml-2 font-normal normal-case text-[var(--text-tertiary)]">
          {shown < total ? `showing ${shown} of ${total}` : `${total}`}
        </span>
      )}
    </span>
  )
}

/** A dedicated full-page search, distinct from ⌘K's quick-jump list: more
 * room per result, searches Events too (the palette doesn't), and is a real
 * bookmarkable/shareable URL (?q=...) rather than a modal. */
export default function Search() {
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const query = params.get('q') ?? ''

  const { data: citizens } = useCitizens()
  const { data: households } = useHouseholds()
  const { data: businesses } = useBusinesses()
  // A deep pull, same rationale as Investigate -- searching Events
  // meaningfully needs real breadth, not just the last page or two.
  const { data: events } = useEvents(3000)

  const q = query.trim().toLowerCase()

  const matchedCitizens = useMemo(
    () => (!q ? [] : (citizens ?? []).filter((c) => c.name.toLowerCase().includes(q) || c.citizen_id.toLowerCase().includes(q) || c.occupation.toLowerCase().includes(q))),
    [citizens, q],
  )
  const matchedHouseholds = useMemo(
    () => (!q ? [] : (households ?? []).filter((h) => h.household_id.toLowerCase().includes(q))),
    [households, q],
  )
  const matchedBusinesses = useMemo(
    () => (!q ? [] : (businesses ?? []).filter((b) => b.business_id.toLowerCase().includes(q) || b.industry.toLowerCase().includes(q))),
    [businesses, q],
  )
  const matchedEvents = useMemo(
    () =>
      !q
        ? []
        : (events ?? []).filter(
            (e) => e.event_type.toLowerCase().includes(q) || e.event_id.toLowerCase().includes(q) || e.source_entity.toLowerCase().includes(q),
          ),
    [events, q],
  )

  const totalMatches = matchedCitizens.length + matchedHouseholds.length + matchedBusinesses.length + matchedEvents.length

  return (
    <div className="flex h-full flex-col">
      <Breadcrumbs items={[{ label: 'Search' }]} />
      <div className="flex flex-col gap-3 px-6 py-4">
        <input
          autoFocus
          value={query}
          onChange={(e) => setParams(e.target.value ? { q: e.target.value } : {})}
          placeholder="Search citizens, households, businesses, events…"
          className="w-full rounded-md border border-[var(--border)] bg-[var(--bg-elevated)] px-3 py-2.5 text-[14px] outline-none focus:border-[var(--accent)]"
        />

        {!q && <div className="px-1 text-[12.5px] text-[var(--text-tertiary)]">Type something above to search across everything.</div>}
        {q && totalMatches === 0 && <div className="px-1 text-[12.5px] text-[var(--text-tertiary)]">No results for "{query}".</div>}

        {q && matchedCitizens.length > 0 && (
          <Panel title={<SectionHeading label="Citizens" shown={Math.min(RESULT_CAP, matchedCitizens.length)} total={matchedCitizens.length} />} padded={false}>
            <div className="max-h-[320px] overflow-y-auto">
              {matchedCitizens.slice(0, RESULT_CAP).map((c) => (
                <button
                  key={c.citizen_id}
                  onClick={() => navigate(`/people/${c.citizen_id}`)}
                  className="flex w-full items-center justify-between border-b border-[var(--border)] px-3 py-2 text-left text-[12.5px] hover:bg-[var(--surface-hover)]"
                >
                  <span className="flex items-center gap-2.5">
                    <span className="font-medium text-[var(--text-secondary)]">{c.name}</span>
                    <span className={c.alive ? 'text-[10.5px] text-[var(--text-tertiary)]' : 'text-[10.5px] text-[var(--danger)]'}>
                      {c.alive ? `age ${c.age} · ${c.occupation}` : 'deceased'}
                    </span>
                  </span>
                  <span className="font-mono text-[10.5px] text-[var(--text-tertiary)]">{c.citizen_id}</span>
                </button>
              ))}
            </div>
          </Panel>
        )}

        {q && matchedHouseholds.length > 0 && (
          <Panel title={<SectionHeading label="Households" shown={Math.min(RESULT_CAP, matchedHouseholds.length)} total={matchedHouseholds.length} />} padded={false}>
            <div className="max-h-[240px] overflow-y-auto">
              {matchedHouseholds.slice(0, RESULT_CAP).map((h) => (
                <button
                  key={h.household_id}
                  onClick={() => navigate(`/people?scope=households&id=${h.household_id}`)}
                  className="flex w-full items-center justify-between border-b border-[var(--border)] px-3 py-2 text-left text-[12.5px] hover:bg-[var(--surface-hover)]"
                >
                  <span className="font-mono">{h.household_id}</span>
                  <span className="text-[10.5px] text-[var(--text-tertiary)]">
                    {h.member_ids.length} member(s) · {(h.financial_stress * 100).toFixed(0)}% stress
                  </span>
                </button>
              ))}
            </div>
          </Panel>
        )}

        {q && matchedBusinesses.length > 0 && (
          <Panel title={<SectionHeading label="Businesses" shown={Math.min(RESULT_CAP, matchedBusinesses.length)} total={matchedBusinesses.length} />} padded={false}>
            <div className="max-h-[240px] overflow-y-auto">
              {matchedBusinesses.slice(0, RESULT_CAP).map((b) => (
                <button
                  key={b.business_id}
                  onClick={() => navigate(`/people?scope=businesses&id=${b.business_id}`)}
                  className="flex w-full items-center justify-between border-b border-[var(--border)] px-3 py-2 text-left text-[12.5px] hover:bg-[var(--surface-hover)]"
                >
                  <span className="flex items-center gap-2.5">
                    <span className="font-mono">{b.business_id}</span>
                    <span className="text-[10.5px] text-[var(--text-tertiary)]">{b.industry.replace(/_/g, ' ')}</span>
                  </span>
                  <span className={b.active ? 'text-[10.5px] text-[var(--success)]' : 'text-[10.5px] text-[var(--danger)]'}>
                    {b.active ? 'active' : 'failed'}
                  </span>
                </button>
              ))}
            </div>
          </Panel>
        )}

        {q && matchedEvents.length > 0 && (
          <Panel title={<SectionHeading label="Events" shown={Math.min(RESULT_CAP, matchedEvents.length)} total={matchedEvents.length} />} padded={false}>
            <div className="max-h-[320px] overflow-y-auto">
              {matchedEvents.slice(0, RESULT_CAP).map((e) => (
                <button
                  key={e.event_id}
                  onClick={() => navigate(`/investigate?trace=${encodeURIComponent(e.event_id)}`)}
                  className="flex w-full items-center justify-between border-b border-[var(--border)] px-3 py-2 text-left font-mono text-[11.5px] hover:bg-[var(--surface-hover)]"
                >
                  <span>D{Math.floor(e.simulation_tick / 24)} · {e.event_type}</span>
                  <span className="text-[var(--text-tertiary)]">{e.source_entity}</span>
                </button>
              ))}
            </div>
          </Panel>
        )}
      </div>
    </div>
  )
}
