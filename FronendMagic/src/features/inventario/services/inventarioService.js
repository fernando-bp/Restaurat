import apiClient from '../../../shared/api/apiClient'

export async function getInventario() {
  const response = await apiClient.get('/inventario/')
  return response.data
}
