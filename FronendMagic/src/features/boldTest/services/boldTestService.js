import apiClient from '../../../shared/api/apiClient'

export async function crearPagoBoldPrueba({ monto, descripcion }) {
  const { data } = await apiClient.post('/bold-test/qr', {
    monto,
    descripcion,
  })
  return data
}

export async function consultarPagoBoldPrueba(id) {
  const { data } = await apiClient.get(`/bold-test/qr/${id}`)
  return data
}
