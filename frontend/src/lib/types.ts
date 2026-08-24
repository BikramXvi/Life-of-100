export interface SimulationStatus {
  simulation_id: string
  tick: number
  day: number
  food_price_index: number
  active_disasters: string[]
  active_disasters_detail: Record<string, { magnitude?: number; started_tick?: number; duration_ticks?: number }>
  policies: Record<string, number>
  population: number
  events_logged: number
  unemployment_rate: number
  active_businesses: number
  health_incidents: number
}

export interface Personality {
  risk_tolerance: number
  ambition: number
  patience: number
  social_tendency: number
}

export interface Citizen {
  citizen_id: string
  name: string
  age: number
  gender: string
  occupation: string
  employer_id: string | null
  salary: number
  savings: number
  debt: number
  assets?: number
  stress: number
  health_score: number
  credit_score?: number | null
  education_level?: string | null
  marital_status?: string | null
  household_id: string
  personality?: Personality
  alive: boolean
  spouse_id?: string | null
  parent_ids?: string[]
  children_ids?: string[]
}

export interface Household {
  household_id: string
  member_ids: string[]
  home_building_id: string | null
  property_value: number
  income: number
  expenses: number
  savings: number
  debt: number
  financial_stress: number
  living_conditions?: string
}

export interface Business {
  business_id: string
  industry: string
  cash: number
  profit: number
  revenue: number
  expenses: number
  active: boolean
  headcount: number
  building_id: string
  employee_ids: string[]
}

export interface WorldZone {
  x: number
  y: number
  kind: string
}

export interface WorldBuilding {
  x: number
  y: number
  kind: string
  building_id: string
}

export interface World {
  city_id: string
  seed: number
  width: number
  height: number
  zones: WorldZone[]
  buildings: WorldBuilding[]
}

export interface SimEvent {
  event_id: string
  event_type: string
  schema_version: number
  simulation_id: string
  simulation_tick: number
  simulation_time: string
  source_entity: string
  source_type: string
  city_id: string
  payload: Record<string, unknown>
  received_at?: string
}

export interface MetricsSeriesPoint {
  tick: number
  day: number
  population: number
  employed: number
  active_businesses: number
  food_price_index: number
  health_incidents: number
  unemployment_proxy: number
}

export interface ExperimentWorldResult {
  name: string
  simulation_id: string
  metrics: Record<string, number>
  pct_change_vs_control?: Record<string, number>
}

export interface ExperimentResult {
  control: { simulation_id: string; metrics: Record<string, number> }
  scenarios: ExperimentWorldResult[]
  ticks: number
}

export interface TippingPoint {
  metric: string
  bracket: [number, number]
  refined_bracket: [number, number] | null
  slope: number
  typical_slope: number
  ratio: number
}

export interface SensitivityResult {
  parameter: string
  values: number[]
  metrics_by_value: Record<string, number>[]
  tipping_points: Record<string, TippingPoint | null>
  methodology: string
}

export interface BranchInfo {
  parent_simulation_id: string
  branch_point_tick: number
  branch_point_day: number
}

export interface SimulationListEntry {
  simulation_id: string
  tick: number
  day: number
  population: number
  branch_info: BranchInfo | null
}

export interface SimulationListResponse {
  active_simulation_id: string
  simulations: SimulationListEntry[]
}

export interface DivergentEvent {
  event_id: string
  event_type: string
  simulation_tick: number
  source_entity: string
}

export interface SimulationCompareResult {
  simulation_a: { simulation_id: string; metrics: Record<string, number> }
  simulation_b: { simulation_id: string; metrics: Record<string, number> }
  divergent_events: Record<string, DivergentEvent[]>
}
