import { useMutation } from '@tanstack/react-query'
import { abrirMesa } from '../services/mesasService'

export function useAbrirMesa() {
  return useMutation({
    mutationFn: ({ mesaId, data }) => abrirMesa(mesaId, data),
  })
}
