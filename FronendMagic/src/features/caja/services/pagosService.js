import apiClient from '../../../shared/api/apiClient'

const pagoPaths = {
  efectivo: '/pagos/efectivo',
  tarjeta_debito: '/pagos/tarjeta',
  tarjeta_credito: '/pagos/tarjeta',
  nequi: '/pagos/transferencia',
  daviplata: '/pagos/transferencia',
  pse: '/pagos/transferencia',
}

export async function registrarPago(data) {
  const path = pagoPaths[data.forma_pago]
  if (!path) {
    throw new Error(`Forma de pago no soportada: ${data.forma_pago}`)
  }
  const response = await apiClient.post(path, data)
  return response.data
}

export async function obtenerEstadoFacturaOrden(orden_id) {
  const response = await apiClient.get(`/facturacion/ordenes/${orden_id}/factura/estado`)
  return response.data
}

export async function cerrarCaja(data) {
  const response = await apiClient.post('/cierre-caja/ejecutar', data)
  return response.data
}

export async function getResumenCierreCaja(fecha) {
  const response = await apiClient.get('/cierre-caja/resumen', {
    params: fecha ? { fecha } : undefined,
  })
  return response.data
}

export async function validarMesasCierreCaja() {
  const response = await apiClient.get('/cierre-caja/validar-mesas')
  return response.data
}
