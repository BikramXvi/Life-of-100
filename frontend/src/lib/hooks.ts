import { useQuery } from '@tanstack/react-query'
import { api } from './api'
import type {
  Business,
  Citizen,
  Household,
  MetricsSeriesPoint,
  SimEvent,
  SimulationListResponse,
  SimulationStatus,
  World,
} from './types'

export function useStatus() {
  return useQuery({
    queryKey: ['status'],
    queryFn: () => api.get<SimulationStatus>('/simulation/status'),
  })
}

export function useCitizens() {
  return useQuery({
    queryKey: ['citizens'],
    queryFn: () => api.get<Citizen[]>('/citizens'),
    refetchInterval: 10000,
  })
}

// The bulk /citizens list is intentionally a lighter payload (no
// personality, marital_status, education_level, credit_score, spouse_id --
// see the API router) so the directory list stays cheap to poll. The detail
// panel needs those fields, so it fetches the single-citizen endpoint too.
export function useCitizenDetail(citizenId: string | undefined) {
  return useQuery({
    queryKey: ['citizen', citizenId],
    queryFn: () => api.get<Citizen>(`/citizens/${citizenId}`),
    enabled: !!citizenId,
  })
}

export function useHouseholds() {
  return useQuery({
    queryKey: ['households'],
    queryFn: () => api.get<Household[]>('/households'),
    refetchInterval: 10000,
  })
}

export function useBusinesses() {
  return useQuery({
    queryKey: ['businesses'],
    queryFn: () => api.get<Business[]>('/businesses'),
    refetchInterval: 10000,
  })
}

export function useWorld() {
  return useQuery({
    queryKey: ['world'],
    queryFn: () => api.get<World>('/world'),
    staleTime: Infinity,
    refetchInterval: false,
  })
}

export function useEvents(limit = 200) {
  return useQuery({
    queryKey: ['events', limit],
    queryFn: () => api.get<SimEvent[]>(`/events?limit=${limit}`),
    refetchInterval: 5000,
  })
}

export function useMetricsSeries() {
  return useQuery({
    queryKey: ['metrics-series'],
    queryFn: () => api.get<MetricsSeriesPoint[]>('/simulation/metrics-timeseries'),
    refetchInterval: 10000,
  })
}

export function useSimulationList() {
  return useQuery({
    queryKey: ['simulation-list'],
    queryFn: () => api.get<SimulationListResponse>('/simulation/list'),
    refetchInterval: 10000,
  })
}

export function useEventVolume() {
  return useQuery({
    queryKey: ['event-volume'],
    queryFn: () => api.get<{ day: number; event_type: string; count: number }[]>('/simulation/event-volume'),
    refetchInterval: 10000,
  })
}
