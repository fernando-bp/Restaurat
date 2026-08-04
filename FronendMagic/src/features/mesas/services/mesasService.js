import apiClient from '../../../shared/api/apiClient'

export async function getMesas(zona) {
  // The backend route is defined with a trailing slash. Request it directly
  // to avoid a redirect that can be downgraded to HTTP behind a proxy.
  const response = await apiClient.get('/mesas/', { params: { zona } })
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
