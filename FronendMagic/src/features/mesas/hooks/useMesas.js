import { useQuery } from '@tanstack/react-query'
import { getMesas } from '../services/mesasService'

export function useMesas(zona) {
  return useQuery({
    queryKey: ['mesas', zona],
    queryFn: () => getMesas(zona),
    keepPreviousData: true,
    select: (data) => data?.mesas ?? [],
  })
}
