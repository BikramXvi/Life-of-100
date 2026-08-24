import DeckGL from '@deck.gl/react'
import { PolygonLayer, LineLayer } from '@deck.gl/layers'
import { useMemo } from 'react'
import type { World, Household, Business, Citizen } from '../../lib/types'

export type VizMode = 'standard' | 'stress' | 'wealth' | 'employment' | 'health' | 'business'

export const VIZ_MODES: { id: VizMode; label: string }[] = [
  { id: 'standard', label: 'Households' },
  { id: 'stress', label: 'Financial Stress' },
  { id: 'wealth', label: 'Wealth' },
  { id: 'employment', label: 'Employment' },
  { id: 'health', label: 'Health' },
  { id: 'business', label: 'Business Activity' },
]

const GRID_SCALE = 0.0012

const ZONE_COLORS: Record<string, [number, number, number, number]> = {
  residential: [26, 46, 38, 210],
  commercial: [20, 40, 62, 210],
  industrial: [52, 40, 26, 210],
  park: [18, 46, 24, 235],
  road: [14, 15, 17, 255],
}

const BUILDING_BASE: Record<string, { color: [number, number, number]; height: number; half: number }> = {
  home: { color: [91, 155, 245], height: 16, half: 0.26 },
  shop: { color: [79, 195, 201], height: 26, half: 0.32 },
  factory: { color: [240, 167, 66], height: 40, half: 0.4 },
  school: { color: [155, 138, 251], height: 32, half: 0.36 },
  hospital: { color: [242, 84, 91], height: 36, half: 0.36 },
  bank: { color: [240, 200, 90], height: 38, half: 0.34 },
  government: { color: [220, 222, 228], height: 50, half: 0.42 },
}

function hashJitter(key: string, spread: number): number {
  let h = 0
  for (let i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) >>> 0
  return ((h % 2001) / 1000 - 1) * spread
}

function lerpColor(a: [number, number, number], b: [number, number, number], t: number): [number, number, number] {
  t = Math.max(0, Math.min(1, t))
  return [Math.round(a[0] + (b[0] - a[0]) * t), Math.round(a[1] + (b[1] - a[1]) * t), Math.round(a[2] + (b[2] - a[2]) * t)]
}

function footprint(x: number, y: number, half: number): [number, number][] {
  const c: [number, number][] = [
    [x - half, y - half],
    [x + half, y - half],
    [x + half, y + half],
    [x - half, y + half],
  ]
  return c.map(([dx, dy]) => [dx * GRID_SCALE, dy * GRID_SCALE])
}

const LOW: [number, number, number] = [62, 207, 142]
const HIGH: [number, number, number] = [242, 84, 91]

export function CityMap({
  world,
  households,
  businesses,
  citizens,
  mode,
  onSelectBuilding,
}: {
  world: World
  households: Household[]
  businesses: Business[]
  citizens: Citizen[]
  mode: VizMode
  onSelectBuilding: (buildingId: string, kind: string) => void
}) {

  const { zoneData, roadSegments, buildingData } = useMemo(() => {
    const householdByBuilding = new Map(households.filter((h) => h.home_building_id).map((h) => [h.home_building_id!, h]))
    const businessByBuilding = new Map(businesses.map((b) => [b.building_id, b]))
    const citizenByHousehold = new Map<string, Citizen[]>()
    for (const c of citizens) {
      const arr = citizenByHousehold.get(c.household_id) ?? []
      arr.push(c)
      citizenByHousehold.set(c.household_id, arr)
    }

    const savingsValues = households.map((h) => h.savings)
    const maxSavings = Math.max(1, ...savingsValues)
    const minSavings = Math.min(0, ...savingsValues)

    const zoneData = world.zones.map((z) => {
      const base = ZONE_COLORS[z.kind] ?? [58, 58, 62, 200]
      const j = hashJitter(`zone_${z.x}_${z.y}`, 6)
      const color: [number, number, number, number] = [
        Math.max(0, Math.min(255, base[0] + j)),
        Math.max(0, Math.min(255, base[1] + j)),
        Math.max(0, Math.min(255, base[2] + j)),
        base[3],
      ]
      return { polygon: footprint(z.x + 0.5, z.y + 0.5, 0.5), color, elevation: z.kind === 'park' ? 3 : 0 }
    })

    const roadCells = new Set(world.zones.filter((z) => z.kind === 'road').map((z) => `${z.x},${z.y}`))
    const roadSegments: { source: [number, number]; target: [number, number] }[] = []
    for (const z of world.zones) {
      if (z.kind !== 'road') continue
      const cx = (z.x + 0.5) * GRID_SCALE
      const cy = (z.y + 0.5) * GRID_SCALE
      for (const [nx, ny] of [[z.x + 1, z.y], [z.x, z.y + 1]] as [number, number][]) {
        if (roadCells.has(`${nx},${ny}`)) {
          roadSegments.push({ source: [cx, cy], target: [(nx + 0.5) * GRID_SCALE, (ny + 0.5) * GRID_SCALE] })
        }
      }
    }

    const buildingData = world.buildings.map((b) => {
      const style = BUILDING_BASE[b.kind] ?? { color: [200, 200, 200] as [number, number, number], height: 20, half: 0.3 }
      let color: [number, number, number] = style.color
      const hh = b.kind === 'home' ? householdByBuilding.get(b.building_id) : undefined
      const biz = b.kind !== 'home' ? businessByBuilding.get(b.building_id) : undefined

      if (hh) {
        const members = citizenByHousehold.get(hh.household_id) ?? []
        if (mode === 'stress') {
          color = lerpColor(LOW, HIGH, hh.financial_stress)
        } else if (mode === 'wealth') {
          const t = (hh.savings - minSavings) / (maxSavings - minSavings || 1)
          color = lerpColor(HIGH, LOW, t)
        } else if (mode === 'employment') {
          const adults = members.filter((c) => c.age >= 18)
          const employed = adults.filter((c) => c.occupation !== 'unemployed' && c.occupation !== 'student')
          const ratio = adults.length ? employed.length / adults.length : 1
          color = lerpColor(HIGH, LOW, ratio)
        } else if (mode === 'health') {
          const avgHealth = members.length ? members.reduce((s, c) => s + c.health_score, 0) / members.length : 1
          color = lerpColor(HIGH, LOW, avgHealth)
        } else {
          const j = hashJitter(b.building_id + 'c', 10)
          color = [
            Math.max(0, Math.min(255, style.color[0] + j)),
            Math.max(0, Math.min(255, style.color[1] + j)),
            Math.max(0, Math.min(255, style.color[2] + j)),
          ]
        }
      } else if (biz && mode === 'business') {
        color = biz.active ? (biz.cash > 0 ? LOW : [240, 167, 66]) : HIGH
      } else {
        const j = hashJitter(b.building_id + 'c', 10)
        color = [
          Math.max(0, Math.min(255, style.color[0] + j)),
          Math.max(0, Math.min(255, style.color[1] + j)),
          Math.max(0, Math.min(255, style.color[2] + j)),
        ]
      }

      const heightJitter = hashJitter(b.building_id + 'h', style.height * 0.18)
      return {
        polygon: footprint(b.x + 0.5, b.y + 0.5, style.half),
        color: [...color, 235] as [number, number, number, number],
        elevation: Math.max(6, style.height + heightJitter),
        kind: b.kind,
        buildingId: b.building_id,
      }
    })

    return { zoneData, roadSegments, buildingData }
  }, [world, households, businesses, citizens, mode])

  const layers = [
    new PolygonLayer({
      id: 'zones',
      data: zoneData,
      getPolygon: (d) => d.polygon,
      getFillColor: (d) => d.color,
      getElevation: (d) => d.elevation,
      extruded: true,
      pickable: false,
    }),
    new LineLayer({
      id: 'roads',
      data: roadSegments,
      getSourcePosition: (d) => d.source,
      getTargetPosition: (d) => d.target,
      getColor: [91, 155, 245, 80],
      getWidth: 2,
      widthMinPixels: 1,
    }),
    new PolygonLayer({
      id: 'buildings',
      data: buildingData,
      getPolygon: (d) => d.polygon,
      getFillColor: (d) => d.color,
      getElevation: (d) => d.elevation,
      extruded: true,
      wireframe: true,
      getLineColor: [91, 155, 245, 110],
      pickable: true,
      autoHighlight: true,
      highlightColor: [255, 255, 255, 60],
      onClick: (info) => {
        if (info.object) onSelectBuilding(info.object.buildingId, info.object.kind)
      },
      material: { ambient: 0.32, diffuse: 0.62, shininess: 36, specularColor: [91, 155, 245] },
    }),
  ]

  const initialViewState = {
    longitude: (world.width / 2) * GRID_SCALE,
    latitude: (world.height / 2) * GRID_SCALE,
    zoom: 14.8,
    pitch: 55,
    bearing: 24,
  }

  return (
    <div className="relative h-full w-full overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border)] bg-[#050607]">
      <DeckGL initialViewState={initialViewState} controller={true} layers={layers} getCursor={() => 'pointer'} />
    </div>
  )
}
