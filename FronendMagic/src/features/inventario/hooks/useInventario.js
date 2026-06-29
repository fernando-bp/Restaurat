import { useQuery } from '@tanstack/react-query'
import { getInventario } from '../services/inventarioService'

export function useInventario() {
  return useQuery({
    queryKey: ['inventario'],
    queryFn: getInventario,
    select: (data) => data ?? [],
  })
}
