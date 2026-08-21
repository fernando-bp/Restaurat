import apiClient from '../../../shared/api/apiClient'

export async function getComandasCocina() {
  const response = await apiClient.get('/cocina/comandas')
  return response.data
}

export async function marcarItemListo(itemId) {
  const response = await apiClient.patch(`/cocina/items/${itemId}/listo`)
  return response.data
}
