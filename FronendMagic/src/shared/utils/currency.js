const copFormatter = new Intl.NumberFormat('es-CO', {
  style: 'currency',
  currency: 'COP',
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
})

const copNumberFormatter = new Intl.NumberFormat('es-CO', {
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
})

export function formatCOP(value) {
  const amount = Number(value)
  return copFormatter.format(Number.isFinite(amount) ? amount : 0)
}

export function formatCOPNumber(value) {
  const amount = Number(value)
  return copNumberFormatter.format(Number.isFinite(amount) ? amount : 0)
}
