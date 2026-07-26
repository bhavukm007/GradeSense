import { useQuery } from '@tanstack/react-query'

import { api } from '../api/client'

export function useRelationshipDiscoveries(limit: number) {
  const early = useQuery({
    queryKey: ['relationship-discovery', 'early', limit],
    queryFn: () => api.relationshipDiscovery('early', limit),
    staleTime: 300_000,
  })
  const middle = useQuery({
    queryKey: ['relationship-discovery', 'middle', limit],
    queryFn: () => api.relationshipDiscovery('middle', limit),
    enabled: early.isSuccess,
    staleTime: 300_000,
  })
  const late = useQuery({
    queryKey: ['relationship-discovery', 'late', limit],
    queryFn: () => api.relationshipDiscovery('late', limit),
    enabled: middle.isSuccess,
    staleTime: 300_000,
  })

  return [early, middle, late] as const
}
