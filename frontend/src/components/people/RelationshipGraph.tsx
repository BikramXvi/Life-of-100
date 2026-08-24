import { useEffect, useMemo, useRef, useState } from 'react'
import { forceSimulation, forceManyBody, forceLink, forceCenter, forceCollide, type SimulationNodeDatum } from 'd3-force'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'

interface RelationshipEdge {
  other_id: string
  other_name: string | null
  relationship_type: string
  strength: number
  trust: number
  frequency: number
}

interface Node extends SimulationNodeDatum {
  id: string
  label: string
  isCenter: boolean
}

const TYPE_COLOR: Record<string, string> = {
  family: '#f2545b',
  friend: '#3ecf8e',
  coworker: '#5b9bf5',
  neighbor: '#f0a742',
}

export function RelationshipGraph({ citizenId, citizenName, onSelect }: { citizenId: string; citizenName: string; onSelect?: (id: string) => void }) {
  const { data: edges } = useQuery({
    queryKey: ['relationships', citizenId],
    queryFn: () => api.get<RelationshipEdge[]>(`/citizens/${citizenId}/relationships`),
    // Relationships change slowly (a few strength-delta events a day) --
    // the app's default 5s poll would otherwise restart this force layout
    // constantly, making node positions (and click targets) drift underfoot.
    staleTime: 30000,
    refetchInterval: false,
  })

  const width = 480
  const height = 320
  const [positions, setPositions] = useState<Map<string, { x: number; y: number }>>(new Map())
  const simRef = useRef<ReturnType<typeof forceSimulation> | null>(null)

  const nodes: Node[] = useMemo(() => {
    const center: Node = { id: citizenId, label: citizenName, isCenter: true, x: width / 2, y: height / 2, fx: width / 2, fy: height / 2 }
    const others: Node[] = (edges ?? []).map((e) => ({ id: e.other_id, label: e.other_name ?? e.other_id, isCenter: false }))
    return [center, ...others]
  }, [edges, citizenId, citizenName])

  useEffect(() => {
    if (!edges) return
    const links = edges.map((e) => ({ source: citizenId, target: e.other_id, strength: e.strength }))
    const sim = forceSimulation(nodes as SimulationNodeDatum[])
      .force('charge', forceManyBody().strength(-220))
      .force(
        'link',
        forceLink(links as any)
          .id((d: any) => d.id)
          .distance((l: any) => 60 + (1 - l.strength) * 80),
      )
      .force('center', forceCenter(width / 2, height / 2))
      .force('collide', forceCollide(28))
      .on('tick', () => {
        const next = new Map<string, { x: number; y: number }>()
        for (const n of nodes as Node[]) {
          next.set(n.id, { x: n.x ?? width / 2, y: n.y ?? height / 2 })
        }
        setPositions(next)
      })
    simRef.current = sim
    return () => {
      sim.stop()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [edges, citizenId])

  if (!edges) return <div className="flex h-[320px] items-center justify-center text-[12.5px] text-[var(--text-tertiary)]">Loading relationships…</div>
  if (edges.length === 0) return <div className="flex h-[320px] items-center justify-center text-[12.5px] text-[var(--text-tertiary)]">No recorded relationships yet.</div>

  return (
    <div>
      <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} className="overflow-visible">
        {edges.map((e) => {
          const p1 = positions.get(citizenId)
          const p2 = positions.get(e.other_id)
          if (!p1 || !p2) return null
          return (
            <line
              key={e.other_id}
              x1={p1.x}
              y1={p1.y}
              x2={p2.x}
              y2={p2.y}
              stroke={TYPE_COLOR[e.relationship_type] ?? 'var(--border-strong)'}
              strokeWidth={1 + e.strength * 2.5}
              strokeOpacity={0.55}
            />
          )
        })}
        {nodes.map((n) => {
          const p = positions.get(n.id) ?? { x: width / 2, y: height / 2 }
          return (
            <g
              key={n.id}
              transform={`translate(${p.x},${p.y})`}
              className={n.isCenter ? '' : 'cursor-pointer'}
              onClick={() => !n.isCenter && onSelect?.(n.id)}
            >
              <circle r={n.isCenter ? 20 : 13} fill={n.isCenter ? 'var(--accent)' : 'var(--surface)'} stroke={n.isCenter ? 'var(--accent)' : 'var(--border-strong)'} strokeWidth={1.5} />
              <text
                y={n.isCenter ? 34 : 26}
                textAnchor="middle"
                fontSize={10.5}
                fill="var(--text-secondary)"
                className="pointer-events-none select-none"
              >
                {n.label.split(' ')[0]}
              </text>
            </g>
          )
        })}
      </svg>
      <div className="mt-2 flex flex-wrap gap-3 text-[10.5px]">
        {Object.entries(TYPE_COLOR).map(([type, color]) => (
          <span key={type} className="flex items-center gap-1.5 text-[var(--text-tertiary)]">
            <span className="h-2 w-2 rounded-full" style={{ background: color }} />
            {type}
          </span>
        ))}
      </div>
    </div>
  )
}
