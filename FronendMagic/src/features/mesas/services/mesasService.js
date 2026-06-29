import apiClient from '../../../shared/api/apiClient'

export async function getMesas(zona) {
  const response = await apiClient.get('/mesas', { params: { zona } })
  return response.data
}

export async function getMesa(mesaId) {
  const response = await apiClient.get(`/mesas/${mesaId}`)
  return response.data
}

export async function abrirMesa(mesaId, data) {
  const response = await apiClient.post(`/mesas/${mesaId}/abrir`, data)
  return response.data
}
