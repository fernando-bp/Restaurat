import apiClient from '../../../shared/api/apiClient'

export async function getRecetas() {
  const response = await apiClient.get('/recetas/')
  return response.data
}

export async function getRecetaDetalle(recetaId) {
  const response = await apiClient.get(`/recetas/${recetaId}`)
  return response.data
}

export async function createReceta(data) {
  const response = await apiClient.post('/recetas/', data)
  return response.data
}

export async function updateReceta(recetaId, data) {
  const response = await apiClient.put(`/recetas/${recetaId}`, data)
  return response.data
}
