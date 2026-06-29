import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { cerrarCaja, getResumenCierreCaja, validarMesasCierreCaja } from '../services/pagosService'

const bills = [100000, 50000, 20000, 10000, 5000, 2000, 1000]
const coins = [500, 200, 100, 50]

const formatCurrency = (value) =>
  new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    maximumFractionDigits: 0,
  }).format(Number(value || 0))

const formatShortDate = (date = new Date()) =>
  date.toLocaleDateString('es-CO', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })

function normalizeMethodName(method = '') {
  const key = method.toLowerCase()
  if (key.includes('efectivo')) return 'Efectivo'
  if (key.includes('tarjeta') || key.includes('debito') || key.includes('credito')) return 'Datafono / Tarjeta'
  if (key.includes('nequi') || key.includes('daviplata') || key.includes('pse') || key.includes('transfer')) {
    return 'Transferencia / Nequi / Daviplata'
  }
  if (key.includes('cortesia')) return 'Cortesia'
  return method || 'Otros'
}

function getMethodTone(method = '') {
  const key = method.toLowerCase()
  if (key.includes('efectivo')) return 'cash'
  if (key.includes('tarjeta') || key.includes('debito') || key.includes('credito')) return 'card'
  return 'transfer'
}

function CountRow({ value, count, onChange, compact = false }) {
  const subtotal = value * count

  return (
    <div className={compact ? 'cash-count-coin' : 'cash-count-row'}>
      <div className="cash-count-denomination">
        <span>{value >= 1000 ? `${value / 1000}k` : `$${value}`}</span>
        <strong>{formatCurrency(value)}</strong>
      </div>
      <div className="cash-count-controls">
        <button type="button" onClick={() => onChange(Math.max(0, count - 1))}>-</button>
        <strong>{count}</strong>
        <button type="button" onClick={() => onChange(count + 1)}>+</button>
      </div>
      <div className="cash-count-subtotal">{subtotal > 0 ? formatCurrency(subtotal) : '-'}</div>
    </div>
  )
}

export default function CierreCajaPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState('conteo')
  const [summary, setSummary] = useState(null)
  const [validation, setValidation] = useState(null)
  const [counts, setCounts] = useState({})
  const [initialFund, setInitialFund] = useState(200000)
  const [observations, setObservations] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [closing, setClosing] = useState(false)
  const [closeResult, setCloseResult] = useState(null)

  const loadCierre = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [resumenData, mesasData] = await Promise.all([
        getResumenCierreCaja(),
        validarMesasCierreCaja(),
      ])
      setSummary(resumenData)
      setValidation(mesasData)
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'No se pudo cargar el cierre de caja.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadCierre()
  }, [loadCierre])

  const totalCounted = useMemo(
    () => [...bills, ...coins].reduce((sum, value) => sum + value * Number(counts[value] || 0), 0),
    [counts],
  )

  const cashSystem = Number(summary?.total_efectivo_sistema || 0)
  const expectedCash = cashSystem + Number(initialFund || 0)
  const difference = totalCounted - expectedCash
  const totalSales = Number(summary?.total_ventas || 0)
  const cardTotal = Number(summary?.total_tarjeta_debito || 0) + Number(summary?.total_tarjeta_credito || 0)
  const transferTotal = Number(summary?.total_transferencia || 0)

  const methodRows = useMemo(() => {
    const grouped = new Map()
    ;(summary?.por_forma_pago || []).forEach((item) => {
      const label = normalizeMethodName(item.forma_pago)
      const existing = grouped.get(label) || { label, total: 0, count: 0, tone: getMethodTone(item.forma_pago) }
      grouped.set(label, {
        ...existing,
        total: existing.total + Number(item.total || 0),
        count: existing.count + Number(item.cantidad_transacciones || 0),
      })
    })

    if (grouped.size === 0) {
      return [
        { label: 'Efectivo', total: cashSystem, count: 0, tone: 'cash' },
        { label: 'Datafono / Tarjeta', total: cardTotal, count: 0, tone: 'card' },
        { label: 'Transferencia / Nequi / Daviplata', total: transferTotal, count: 0, tone: 'transfer' },
      ]
    }

    return Array.from(grouped.values())
  }, [summary, cashSystem, cardTotal, transferTotal])

  const handleCountChange = (value, nextCount) => {
    setCounts((current) => ({ ...current, [value]: nextCount }))
  }

  const handleClose = async () => {
    setClosing(true)
    setError('')
    try {
      const result = await cerrarCaja({
        efectivo_contado: {
          billetes: bills.map((denominacion) => ({
            denominacion,
            cantidad: Number(counts[denominacion] || 0),
          })),
          monedas: coins.map((denominacion) => ({
            denominacion,
            cantidad: Number(counts[denominacion] || 0),
          })),
        },
        observaciones: observations || undefined,
      })
      setCloseResult(result)
      setCounts({})
      setInitialFund(200000)
      setObservations('')
      await loadCierre()
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'No se pudo ejecutar el cierre de caja.')
    } finally {
      setClosing(false)
    }
  }

  const progress = [
    { id: 'conteo', label: 'Conteo efectivo' },
    { id: 'resumen', label: 'Resumen ventas' },
    { id: 'cierre', label: 'Cierre de caja' },
  ]

  return (
    <div className="daily-close-page">
      <header className="daily-close-header">
        <div className="daily-close-title">
          <button type="button" onClick={() => navigate('/mesas')} aria-label="Volver">←</button>
          <span className="daily-close-lock">□</span>
          <div>
            <h1>Cierre de Caja</h1>
            <p>{formatShortDate()}</p>
          </div>
        </div>

        <div className="daily-close-metrics">
          <div>
            <span>Ventas del corte</span>
            <strong>{formatCurrency(totalSales)}</strong>
          </div>
          <div>
            <span>Conteo caja</span>
            <strong className={difference < 0 ? 'is-danger' : ''}>{formatCurrency(totalCounted)}</strong>
          </div>
        </div>
      </header>

      <nav className="daily-close-tabs">
        {progress.map((item, index) => (
          <button
            key={item.id}
            type="button"
            className={step === item.id ? 'active' : ''}
            onClick={() => setStep(item.id)}
          >
            <span>{closeResult || progress.findIndex((p) => p.id === step) > index ? '✓' : index + 1}</span>
            {item.label}
          </button>
        ))}
      </nav>

      {loading ? (
        <div className="daily-close-state">Cargando cierre de caja...</div>
      ) : error ? (
        <div className="daily-close-alert daily-close-alert--danger">{error}</div>
      ) : null}

      {!loading ? (
        <main className="daily-close-layout">
          <section className="daily-close-main">
            {step === 'conteo' ? (
              <>
                <div className="cash-count-list">
                  {bills.map((value) => (
                    <CountRow
                      key={value}
                      value={value}
                      count={Number(counts[value] || 0)}
                      onChange={(nextCount) => handleCountChange(value, nextCount)}
                    />
                  ))}
                </div>

                <section className="cash-coins-panel">
                  <h2>Monedas</h2>
                  <div className="cash-coins-grid">
                    {coins.map((value) => (
                      <CountRow
                        key={value}
                        value={value}
                        compact
                        count={Number(counts[value] || 0)}
                        onChange={(nextCount) => handleCountChange(value, nextCount)}
                      />
                    ))}
                  </div>
                </section>
              </>
            ) : null}

            {step === 'resumen' ? (
              <section className="sales-summary-list">
                {methodRows.map((item) => (
                  <button key={item.label} type="button" className={`sales-summary-row sales-summary-row--${item.tone}`}>
                    <span className="sales-summary-icon" />
                    <span>
                      <strong>{item.label}</strong>
                      <small>{item.count} transacciones en corte</small>
                    </span>
                    <b>{formatCurrency(item.total)}</b>
                  </button>
                ))}
              </section>
            ) : null}

            {step === 'cierre' ? (
              <section className="close-review">
                {Math.abs(difference) > 100 ? (
                  <div className="daily-close-alert daily-close-alert--danger">
                    <strong>Descuadre detectado</strong>
                    <span>Diferencia de {formatCurrency(Math.abs(difference))} {difference < 0 ? 'faltante' : 'sobrante'}</span>
                  </div>
                ) : (
                  <div className="daily-close-alert daily-close-alert--ok">
                    <strong>Caja cuadrada</strong>
                    <span>La diferencia esta dentro de la tolerancia.</span>
                  </div>
                )}

                <div className="close-review-card">
                  <h2>Cuadre de caja</h2>
                  <div><span>Ventas en efectivo</span><strong>{formatCurrency(cashSystem)}</strong></div>
                  <div><span>Fondo inicial</span><strong>{formatCurrency(initialFund)}</strong></div>
                  <div><span>Total esperado</span><strong>{formatCurrency(expectedCash)}</strong></div>
                  <div><span>Conteo fisico</span><strong>{formatCurrency(totalCounted)}</strong></div>
                  <div className="close-review-card__total"><span>Diferencia</span><strong>{formatCurrency(difference)}</strong></div>
                </div>

                <div className="close-review-card">
                  <h2>Total por metodo de pago</h2>
                  {methodRows.map((item) => (
                    <div key={item.label}>
                      <span>{item.label}</span>
                      <strong>{formatCurrency(item.total)}</strong>
                    </div>
                  ))}
                </div>

                {closeResult ? (
                  <div className="daily-close-alert daily-close-alert--ok">
                    <strong>Cierre registrado</strong>
                    <span>Consecutivo #{closeResult.id} para {closeResult.fecha}</span>
                  </div>
                ) : null}
              </section>
            ) : null}
          </section>

          <aside className="daily-close-sidebar">
            {step === 'conteo' ? (
              <>
                <div className="close-side-card">
                  <h2>Fondo inicial de caja</h2>
                  <label className="close-money-input">
                    <span>$</span>
                    <input
                      type="number"
                      min={0}
                      value={initialFund}
                      onChange={(event) => setInitialFund(Number(event.target.value))}
                    />
                  </label>
                </div>
                <div className="close-total-card">
                  <h2>Total contado</h2>
                  <strong>{formatCurrency(totalCounted)}</strong>
                  <div className="close-total-lines">
                    {[...bills, ...coins].filter((value) => counts[value] > 0).map((value) => (
                      <div key={value}>
                        <span>{formatCurrency(value)} x {counts[value]}</span>
                        <b>{formatCurrency(value * counts[value])}</b>
                      </div>
                    ))}
                    {totalCounted === 0 ? <p>Ingresa las cantidades...</p> : null}
                  </div>
                </div>
                <button type="button" className="daily-close-primary" onClick={() => setStep('resumen')}>
                  Ver resumen de ventas
                </button>
              </>
            ) : null}

            {step === 'resumen' ? (
              <>
                <div className="close-side-card">
                  <h2>Distribucion de ventas</h2>
                  <div className="sales-bars">
                    {methodRows.map((item) => {
                      const pct = totalSales > 0 ? Math.round((item.total / totalSales) * 100) : 0
                      return (
                        <div key={item.label} className={`sales-bar sales-bar--${item.tone}`}>
                          <div><span>{item.label}</span><b>{formatCurrency(item.total)}</b></div>
                          <i><span style={{ width: `${pct}%` }} /></i>
                          <small>{pct}%</small>
                        </div>
                      )
                    })}
                  </div>
                  <div className="sales-total">
                    <span>Total ventas</span>
                    <strong>{formatCurrency(totalSales)}</strong>
                  </div>
                </div>
                <button type="button" className="daily-close-primary daily-close-primary--green" onClick={() => setStep('cierre')}>
                  Proceder al cierre
                </button>
              </>
            ) : null}

            {step === 'cierre' ? (
              <>
                <div className="close-side-card">
                  <h2>Observaciones del turno</h2>
                  <textarea
                    value={observations}
                    onChange={(event) => setObservations(event.target.value)}
                    placeholder="Novedades, faltantes, incidencias..."
                  />
                </div>
                <div className="close-side-card">
                  <h2>Resumen final</h2>
                  <div className="close-final-row"><span>Total ventas</span><strong>{formatCurrency(totalSales)}</strong></div>
                  <div className="close-final-row"><span>Conteo fisico</span><strong>{formatCurrency(totalCounted)}</strong></div>
                  <div className="close-final-row"><span>Diferencia</span><strong className={difference < 0 ? 'is-danger' : ''}>{formatCurrency(difference)}</strong></div>
                </div>
                {validation && !validation.todas_cerradas ? (
                  <div className="daily-close-alert daily-close-alert--danger">
                    <strong>Mesas abiertas</strong>
                    <span>{validation.mensaje}</span>
                  </div>
                ) : null}
                <button
                  type="button"
                  className="daily-close-primary daily-close-primary--green"
                  onClick={handleClose}
                  disabled={closing || validation?.todas_cerradas === false || Boolean(closeResult)}
                >
                  {closing ? 'Cerrando...' : closeResult ? 'Cierre registrado' : 'Cerrar caja'}
                </button>
              </>
            ) : null}
          </aside>
        </main>
      ) : null}
    </div>
  )
}
