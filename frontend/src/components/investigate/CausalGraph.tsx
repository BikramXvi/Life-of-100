import { useEffect, useMemo, useRef, useState } from 'react'
import type { SimEvent } from '../../lib/types'

interface GraphNode {
  event: SimEvent
  level: number
  x: number
  parentId: string | null
  isTarget: boolean
}

const CAUSE_KEYS = ['caused_by', 'caused_by_disaster_event_id', 'proposed_event_id'] as const

function linkedCauseId(e: SimEvent): string | undefined {
  for (const k of CAUSE_KEYS) {
    const v = e.payload[k]
    if (v) return String(v)
  }
  return undefined
}

const TYPE_COLOR: Record<string, string> = {
  DISASTER_STARTED: 'var(--danger)',
  DISASTER_ENDED: 'var(--success)',
  JOB_LOST: 'var(--danger)',
  BUSINESS_FAILED: 'var(--danger)',
  BUSINESS_CONTRACTED: 'var(--warning)',
  PRICE_CHANGED: 'var(--warning)',
  HEALTH_IMPACTED: 'var(--danger)',
  CITIZEN_DIED: 'var(--danger)',
  JOB_STARTED: 'var(--success)',
  MARRIAGE: 'var(--success)',
  CHILD_BORN: 'var(--success)',
  POLICY_CHANGED: 'var(--accent)',
  AI_DECISION_PROPOSED: 'var(--violet)',
  AI_DECISION_ACCEPTED: 'var(--violet)',
  AI_DECISION_REJECTED: 'var(--danger)',
}
const DEFAULT_COLOR = 'var(--text-tertiary)'

const MAX_DEPTH = 4
const MAX_EFFECT_NODES = 60

/** Builds a real multi-level causal graph: the (always-linear) chain of
 * recorded causes back to the root, PLUS the full branching tree of
 * everything downstream -- effects of effects, recursively, not just the
 * one hop the raw /effects endpoint returns. Built entirely from the
 * already-fetched event log (no extra API calls), since a "cause" is just
 * an explicit payload pointer -- never inferred, matching causality.py's
 * own discipline. */
function buildGraph(allEvents: SimEvent[], targetId: string) {
  const byId = new Map(allEvents.map((e) => [e.event_id, e]))
  const effectsOf = new Map<string, SimEvent[]>()
  for (const e of allEvents) {
    const cause = linkedCauseId(e)
    if (!cause) continue
    const arr = effectsOf.get(cause) ?? []
    arr.push(e)
    effectsOf.set(cause, arr)
  }

  const nodes: GraphNode[] = []
  const edges: { from: string; to: string }[] = []

  // Backward chain: target at level 0, root cause at the most negative level.
  const chain: SimEvent[] = []
  let cur: SimEvent | undefined = byId.get(targetId)
  const seenBack = new Set<string>()
  while (cur && !seenBack.has(cur.event_id) && chain.length < 10) {
    seenBack.add(cur.event_id)
    chain.push(cur)
    const nextId = linkedCauseId(cur)
    cur = nextId ? byId.get(nextId) : undefined
  }
  chain.reverse() // root first
  const rootLevel = -(chain.length - 1)
  chain.forEach((e, i) => {
    const level = rootLevel + i
    nodes.push({ event: e, level, x: 0, parentId: i > 0 ? chain[i - 1].event_id : null, isTarget: e.event_id === targetId })
    if (i > 0) edges.push({ from: chain[i - 1].event_id, to: e.event_id })
  })

  // Forward tree: BFS from target through effectsOf, level 1, 2, 3...
  let frontier = [targetId]
  const seenForward = new Set(chain.map((e) => e.event_id))
  let level = 1
  let count = 0
  while (frontier.length && level <= MAX_DEPTH && count < MAX_EFFECT_NODES) {
    const next: string[] = []
    for (const parentId of frontier) {
      for (const child of effectsOf.get(parentId) ?? []) {
        if (seenForward.has(child.event_id)) continue
        seenForward.add(child.event_id)
        nodes.push({ event: child, level, x: 0, parentId, isTarget: false })
        edges.push({ from: parentId, to: child.event_id })
        next.push(child.event_id)
        count++
        if (count >= MAX_EFFECT_NODES) break
      }
      if (count >= MAX_EFFECT_NODES) break
    }
    frontier = next
    level++
  }

  // Assign x positions: evenly spread within each level.
  const byLevel = new Map<number, GraphNode[]>()
  for (const n of nodes) {
    const arr = byLevel.get(n.level) ?? []
    arr.push(n)
    byLevel.set(n.level, arr)
  }
  for (const arr of byLevel.values()) {
    arr.forEach((n, i) => {
      n.x = (i + 0.5) / arr.length
    })
  }

  return { nodes, edges, truncated: count >= MAX_EFFECT_NODES }
}

export function CausalGraph({
  events,
  targetId,
  onSelectEvent,
}: {
  events: SimEvent[]
  targetId: string
  onSelectEvent: (id: string) => void
}) {
  const { nodes, edges, truncated } = useMemo(() => buildGraph(events, targetId), [events, targetId])
  const [hoveredId, setHoveredId] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  const levels = Array.from(new Set(nodes.map((n) => n.level))).sort((a, b) => a - b)
  const levelHeight = 78
  const NODE_SLOT = 148 // min horizontal space per node so labels never overlap
  const maxNodesInLevel = Math.max(1, ...levels.map((lv) => nodes.filter((n) => n.level === lv).length))
  const width = Math.max(720, maxNodesInLevel * NODE_SLOT)
  const height = levels.length * levelHeight + 40
  const yFor = (level: number) => 30 + (levels.indexOf(level) + 0.5) * levelHeight
  const posById = new Map(nodes.map((n) => [n.event.event_id, { x: 20 + n.x * (width - 40), y: yFor(n.level) }]))

  // The traced node can land anywhere along a canvas that's scaled to fit the
  // widest level (e.g. dead center, if it's a lone root above 47 spread-out
  // effects) -- without this the most relevant node is silently off-screen
  // at the default scrollLeft: 0 and the user has to go hunting for it.
  useEffect(() => {
    const el = scrollRef.current
    const targetPos = posById.get(targetId)
    if (!el || !targetPos) return
    el.scrollLeft = Math.max(0, targetPos.x - el.clientWidth / 2)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [targetId, width])

  if (nodes.length === 0) {
    return <div className="text-[12.5px] text-[var(--text-tertiary)]">Event not found in the loaded log.</div>
  }

  return (
    <div>
      <div ref={scrollRef} className="overflow-x-auto">
        <svg width={width} height={height} className="min-w-full">
          {edges.map((e, i) => {
            const p1 = posById.get(e.from)
            const p2 = posById.get(e.to)
            if (!p1 || !p2) return null
            const midY = (p1.y + p2.y) / 2
            return (
              <path
                key={i}
                d={`M ${p1.x} ${p1.y} C ${p1.x} ${midY}, ${p2.x} ${midY}, ${p2.x} ${p2.y}`}
                fill="none"
                stroke={hoveredId && (e.from === hoveredId || e.to === hoveredId) ? 'var(--accent)' : 'var(--border-strong)'}
                strokeWidth={hoveredId && (e.from === hoveredId || e.to === hoveredId) ? 2 : 1.25}
              />
            )
          })}
          {nodes.map((n) => {
            const p = posById.get(n.event.event_id)!
            const color = TYPE_COLOR[n.event.event_type] ?? DEFAULT_COLOR
            return (
              <g
                key={n.event.event_id}
                transform={`translate(${p.x},${p.y})`}
                className="cursor-pointer"
                onMouseEnter={() => setHoveredId(n.event.event_id)}
                onMouseLeave={() => setHoveredId((id) => (id === n.event.event_id ? null : id))}
                onClick={() => onSelectEvent(n.event.event_id)}
              >
                <rect
                  x={-64}
                  y={-16}
                  width={128}
                  height={32}
                  rx={4}
                  fill="var(--bg-elevated)"
                  stroke={n.isTarget ? 'var(--accent)' : color}
                  strokeWidth={n.isTarget ? 2 : 1.25}
                />
                <text y={-2} textAnchor="middle" fontSize={9.5} fontWeight={600} fill="var(--text-primary)" className="select-none">
                  {n.event.event_type.replace(/_/g, ' ').slice(0, 20)}
                </text>
                <text y={10} textAnchor="middle" fontSize={8.5} fill="var(--text-tertiary)" className="select-none font-mono">
                  D{Math.floor(n.event.simulation_tick / 24)} · {n.event.source_entity.slice(0, 14)}
                </text>
              </g>
            )
          })}
        </svg>
      </div>
      {truncated && <div className="mt-1 text-[11px] text-[var(--text-tertiary)]">Downstream tree truncated at {MAX_EFFECT_NODES} nodes / depth {MAX_DEPTH} for readability.</div>}
      <div className="mt-2 flex flex-wrap gap-3 text-[10.5px]">
        <span className="flex items-center gap-1.5 text-[var(--text-tertiary)]"><span className="h-2 w-2 rounded-sm border-2 border-[var(--accent)]" />traced event</span>
        <span className="flex items-center gap-1.5 text-[var(--text-tertiary)]"><span className="h-2 w-2 rounded-sm bg-[var(--danger)]" />negative</span>
        <span className="flex items-center gap-1.5 text-[var(--text-tertiary)]"><span className="h-2 w-2 rounded-sm bg-[var(--success)]" />positive</span>
        <span className="flex items-center gap-1.5 text-[var(--text-tertiary)]"><span className="h-2 w-2 rounded-sm bg-[var(--violet)]" />AI decision</span>
      </div>
    </div>
  )
}
