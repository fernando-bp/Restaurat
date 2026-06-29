import apiClient from '../../../shared/api/apiClient'

export async function getReporteFinanciero(params = {}) {
  const cleanParams = Object.entries(params).reduce((acc, [key, value]) => {
    if (value !== '' && value !== null && value !== undefined) acc[key] = value
    return acc
  }, {})
  const response = await apiClient.get('/reportes-financieros/', { params: cleanParams })
  return response.data
}
