import apiClient from '../../../shared/api/apiClient'

export async function getReporteFinanciero(params = {}) {
  const cleanParams = Object.entries(params).reduce((acc, [key, value]) => {
    if (value !== '' && value !== null && value !== undefined) acc[key] = value
    return acc
  }, {})
  const response = await apiClient.get('/reportes-financieros/', { params: cleanParams })
  return response.data
}

export async function getEstadoFacturaOrden(ordenId) {
  const response = await apiClient.get(`/facturacion/ordenes/${ordenId}/factura/estado`)
  return response.data
}

export async function getEstadosFacturaOrdenes(ordenIds = []) {
  const entries = await Promise.all(
    ordenIds.map(async (ordenId) => {
      try {
        const estado = await getEstadoFacturaOrden(ordenId)
        return [ordenId, estado]
      } catch (error) {
        return [ordenId, {
          orden_id: ordenId,
          estado: 'error',
          ultimo_error: error?.response?.data?.detail || error.message || 'No se pudo consultar la factura.',
        }]
      }
    }),
  )
  return Object.fromEntries(entries)
}
