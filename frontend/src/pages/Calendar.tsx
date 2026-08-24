import { useMemo, useState } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import clsx from 'clsx'
import { Breadcrumbs } from '../components/ui/Breadcrumbs'
import { Panel } from '../components/ui/Panel'
import { useEvents } from '../lib/hooks'
import type { SimEvent } from '../lib/types'

const LIFE_EVENT_TYPES = new Set(['CHILD_BORN', 'CITIZEN_DIED', 'MARRIAGE', 'DIVORCE', 'JOB_LOST', 'JOB_STARTED', 'DISASTER_STARTED', 'POLICY_CHANGED'])

const EVENT_DOT: Record<string, string> = {
  CHILD_BORN: 'var(--success)',
  MARRIAGE: 'var(--success)',
  JOB_STARTED: 'var(--success)',
  CITIZEN_DIED: 'var(--danger)',
  DIVORCE: 'var(--danger)',
  JOB_LOST: 'var(--danger)',
  DISASTER_STARTED: 'var(--danger)',
  POLICY_CHANGED: 'var(--accent)',
}

const DAYS_PER_MONTH = 30
const MONTHS_PER_YEAR = 12 // 360 sim-days/year, matching engine.py's 30-day months (365 total, last month short)

function dayToYMD(day: number) {
  const year = Math.floor(day / 365) + 1
  const dayOfYear = day % 365
  const month = Math.min(MONTHS_PER_YEAR, Math.floor(dayOfYear / DAYS_PER_MONTH) + 1)
  const dayOfMonth = (dayOfYear % DAYS_PER_MONTH) + 1
  return { year, month, dayOfMonth }
}

export default function CalendarPage() {
  const { data: events } = useEvents(2000)
  const [monthOffset, setMonthOffset] = useState(0)
  const [selectedDay, setSelectedDay] = useState<number | null>(null)

  const maxDay = useMemo(() => Math.max(0, ...(events ?? []).map((e) => Math.floor(e.simulation_tick / 24))), [events])
  const { year: curYear, month: curMonth } = dayToYMD(maxDay)

  // Navigate by whole simulated months (30 days), clamped to what's been simulated.
  const viewedMonthIndex = (curYear - 1) * MONTHS_PER_YEAR + (curMonth - 1) + monthOffset
  const viewedYear = Math.floor(viewedMonthIndex / MONTHS_PER_YEAR) + 1
  const viewedMonth = (viewedMonthIndex % MONTHS_PER_YEAR) + 1
  const monthStartDay = (viewedYear - 1) * 365 + (viewedMonth - 1) * DAYS_PER_MONTH

  const eventsByDay = useMemo(() => {
    const map = new Map<number, SimEvent[]>()
    for (const e of events ?? []) {
      if (!LIFE_EVENT_TYPES.has(e.event_type)) continue
      const day = Math.floor(e.simulation_tick / 24)
      const arr = map.get(day) ?? []
      arr.push(e)
      map.set(day, arr)
    }
    return map
  }, [events])

  const days = Array.from({ length: DAYS_PER_MONTH }, (_, i) => monthStartDay + i)
  const selectedEvents = selectedDay != null ? eventsByDay.get(selectedDay) ?? [] : []

  return (
    <div className="flex h-full flex-col">
      <Breadcrumbs items={[{ label: 'Calendar' }]} />
      <div className="grid grid-cols-[1fr_320px] gap-3 px-6 py-4">
        <Panel
          title={`Year ${viewedYear} · Month ${viewedMonth}`}
          subtitle="Life events by simulated day (30-day months)"
          action={
            <div className="flex gap-1">
              <button onClick={() => setMonthOffset((o) => o - 1)} className="rounded p-1 hover:bg-[var(--surface-hover)]">
                <ChevronLeft size={15} />
              </button>
              <button
                onClick={() => setMonthOffset((o) => Math.min(0, o + 1))}
                disabled={monthOffset >= 0}
                className="rounded p-1 hover:bg-[var(--surface-hover)] disabled:opacity-30"
              >
                <ChevronRight size={15} />
              </button>
            </div>
          }
        >
          <div className="grid grid-cols-6 gap-2">
            {days.map((day) => {
              const dayEvents = eventsByDay.get(day) ?? []
              const isFuture = day > maxDay
              return (
                <button
                  key={day}
                  onClick={() => !isFuture && setSelectedDay(day)}
                  disabled={isFuture}
                  className={clsx(
                    'flex h-20 flex-col items-start rounded-md border p-2 text-left transition-colors',
                    isFuture ? 'border-[var(--border)] opacity-30' : 'border-[var(--border)] hover:border-[var(--border-strong)]',
                    selectedDay === day && 'border-[var(--accent)] bg-[var(--accent-dim)]',
                  )}
                >
                  <span className="font-mono text-[11px] text-[var(--text-tertiary)]">D{day}</span>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {dayEvents.slice(0, 6).map((e, i) => (
                      <span key={i} className="h-1.5 w-1.5 rounded-full" style={{ background: EVENT_DOT[e.event_type] ?? 'var(--text-tertiary)' }} title={e.event_type} />
                    ))}
                  </div>
                  {dayEvents.length > 0 && <span className="mt-auto text-[10px] text-[var(--text-tertiary)]">{dayEvents.length} event(s)</span>}
                </button>
              )
            })}
          </div>
        </Panel>

        <Panel title={selectedDay != null ? `Day ${selectedDay}` : 'Select a day'}>
          {selectedDay == null && <div className="text-[12.5px] text-[var(--text-tertiary)]">Click a day with events to see details.</div>}
          {selectedEvents.map((e) => (
            <div key={e.event_id} className="mb-2 border-b border-[var(--border)] pb-2 last:border-0">
              <div className="flex items-center gap-2 text-[12.5px] font-medium">
                <span className="h-2 w-2 rounded-full" style={{ background: EVENT_DOT[e.event_type] ?? 'var(--text-tertiary)' }} />
                {e.event_type.replace(/_/g, ' ')}
              </div>
              <div className="mt-0.5 font-mono text-[11px] text-[var(--text-tertiary)]">{e.source_entity}</div>
            </div>
          ))}
        </Panel>
      </div>
    </div>
  )
}
