import apiClient from '../../../shared/api/apiClient'

export async function getRecetas() {
  const response = await apiClient.get('/recetas')
  return response.data
}

export async function getOrden(ordenId) {
  const response = await apiClient.get(`/ordenes/${ordenId}`)
  return response.data
}

export async function crearOrden(data) {
  const response = await apiClient.post('/ordenes', data)
  return response.data
}

export async function agregarItem(ordenId, data) {
  const response = await apiClient.post('/ordenes', data)
  return response.data
}

export async function actualizarItem(ordenId, itemId, data) {
  const response = await apiClient.patch(`/ordenes/${ordenId}/items/${itemId}`, data)
  return response.data
}

export async function eliminarItem(ordenId, itemId) {
  const response = await apiClient.delete(`/ordenes/${ordenId}/items/${itemId}`)
  return response.data
}

export async function confirmarOrden(ordenId) {
  const response = await apiClient.post(`/ordenes/${ordenId}/confirmar`)
  return response.data
}
