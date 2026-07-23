import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { consultarPagoBoldPrueba, crearPagoBoldPrueba } from '../services/boldTestService'
import { formatCOP } from '../../../shared/utils/currency'

function getStatusClass(status) {
  const value = String(status || '').toLowerCase()
  if (value === 'aprobado') return 'is-approved'
  if (value === 'rechazado' || value === 'error') return 'is-rejected'
  if (value === 'expirado' || value === 'anulado') return 'is-expired'
  return 'is-pending'
}

function buildQrImageUrl(payment) {
  if (!payment) return ''
  if (payment.qr_url) return payment.qr_url

  const content = payment.qr_payload
  if (!content) return ''
  if (/^[A-Za-z0-9+/]+={0,2}$/.test(content) && content.length > 120) {
    return `data:image/png;base64,${content}`
  }

  return `https://api.qrserver.com/v1/create-qr-code/?size=260x260&data=${encodeURIComponent(content)}`
}

export default function BoldTestPage() {
  const navigate = useNavigate()
  const [monto, setMonto] = useState(2200)
  const [payment, setPayment] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const qrImageUrl = useMemo(() => buildQrImageUrl(payment), [payment])

  useEffect(() => {
    if (!payment?.id || !['PENDIENTE'].includes(payment.estado)) return undefined

    const timer = setInterval(async () => {
      try {
        const nextPayment = await consultarPagoBoldPrueba(payment.id)
        setPayment((current) => ({ ...current, ...nextPayment }))
      } catch (err) {
        setError(err?.response?.data?.detail || err.message || 'No se pudo consultar el estado')
      }
    }, 5000)

    return () => clearInterval(timer)
  }, [payment?.id, payment?.estado])

  const handleCreate = async (event) => {
    event.preventDefault()
    setError('')
    setLoading(true)
    setPayment(null)

    try {
      const created = await crearPagoBoldPrueba({
        monto: Number(monto),
        descripcion: 'Pago QR Bre-B prueba POS',
      })
      setPayment(created)
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'No se pudo generar el QR dinamico')
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    if (!payment?.id) return
    setError('')
    try {
      const nextPayment = await consultarPagoBoldPrueba(payment.id)
      setPayment((current) => ({ ...current, ...nextPayment }))
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'No se pudo consultar el estado')
    }
  }

  return (
    <div className="bold-test-page">
      <header className="bold-test-header">
        <button type="button" onClick={() => navigate('/mesas')}>Volver</button>
        <div>
          <span>Laboratorio independiente</span>
          <h1>Pago QR Bre-B prueba</h1>
        </div>
      </header>

      <main className="bold-test-layout">
        <section className="bold-test-panel">
          <form onSubmit={handleCreate} className="bold-test-form">
            <label>
              <span>Monto de prueba</span>
              <div className="bold-test-money">
                <b>$</b>
                <input
                  type="number"
                  min={1000}
                  step={1}
                  value={monto}
                  onChange={(event) => setMonto(event.target.value)}
                />
              </div>
            </label>

            <div className="bold-test-quick">
              {[2200, 5000, 10000].map((value) => (
                <button key={value} type="button" onClick={() => setMonto(value)}>
                  {formatCOP(value)}
                </button>
              ))}
            </div>

            <button type="submit" className="bold-test-primary" disabled={loading || Number(monto) < 1000}>
              {loading ? 'Generando...' : 'Generar QR dinamico'}
            </button>
          </form>

          {error ? <div className="bold-test-error">{error}</div> : null}
        </section>

        <section className="bold-test-result">
            {payment ? (
            <>
              <div className="bold-test-result__top">
                <div>
                  <span>Estado</span>
                  <strong className={getStatusClass(payment.estado)}>{payment.estado}</strong>
                </div>
                <button type="button" onClick={handleRefresh}>Actualizar</button>
              </div>

              <div className="bold-test-qr">
                {qrImageUrl ? (
                  <img src={qrImageUrl} alt="QR dinamico Bold con monto precargado" />
                ) : (
                  <div className="bold-test-qr__empty">QR no disponible</div>
                )}
              </div>

              <p className="bold-test-scan-note">
                Escanea este QR desde Nequi, Daviplata o una app bancaria compatible. El monto ya va precargado.
              </p>

              <div className="bold-test-details">
                <div>
                  <span>Monto</span>
                  <strong>{formatCOP(payment.monto)}</strong>
                </div>
                <div>
                  <span>Referencia</span>
                  <strong>{payment.referencia}</strong>
                </div>
                <div>
                  <span>Metodo</span>
                  <strong>{payment.metodo_pago || 'QR_BREB'}</strong>
                </div>
                <div>
                  <span>Contenido QR</span>
                  <strong>{payment.qr_payload || payment.qr_url || 'Referencia de prueba'}</strong>
                </div>
              </div>
            </>
          ) : (
            <div className="bold-test-empty">
              <strong>Listo para prueba</strong>
              <span>Genera un QR dinamico Bre-B con el monto precargado. Este flujo no registra pagos en el POS.</span>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
