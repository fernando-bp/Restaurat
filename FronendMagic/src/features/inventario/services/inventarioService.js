import apiClient from '../../../shared/api/apiClient'

export async function getInventario() {
  const response = await apiClient.get('/inventario/')
  return response.data
}

export async function actualizarStockInventario(inventarioId, stockActual) {
  const response = await apiClient.patch(`/inventario/${inventarioId}/stock`, {
    stock_actual: stockActual,
  })
  return response.data
}
