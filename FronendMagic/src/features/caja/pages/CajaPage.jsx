import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getMesa } from '../../mesas/services/mesasService'
import { getOrden, getRecetas } from '../../ordenes/services/ordenesService'
import { crearPagoBoldTerminal, getBoldTerminalAvailability, getPagoBoldTerminal, obtenerEstadoFacturaOrden, registrarPago, verificarPagoBoldTerminal } from '../services/pagosService'
import DividirCuenta from '../components/DividirCuenta'
import { formatCOP, formatCOPNumber } from '../../../shared/utils/currency'

const paymentMethods = [
  { id: 'efectivo', label: 'Efectivo', icon: '💵' },
  { id: 'tarjeta_debito', label: 'Débito', icon: '💳' },
  { id: 'tarjeta_credito', label: 'Crédito', icon: '💳' },
  { id: 'nequi', label: 'Nequi / PSE', icon: '📲' },
]

function formatElapsed(horaApertura) {
  if (!horaApertura) return null
  const diff = Math.floor((Date.now() - new Date(horaApertura).getTime()) / 1000)
  if (diff < 60) return `${diff}s`
  const m = Math.floor(diff / 60)
  if (m < 60) return `${m}min`
  return `${Math.floor(m / 60)}h ${m % 60}min`
}

const maxInvoicePollAttempts = 12
const TAX_RATE = 0.08

const normalizeDbName = (value = '') =>
  String(value)
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^\w\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

const displayNameOverrides = {
  'des amer': 'Desayuno Americano',
  'des cont': 'Desayuno Continental',
  'des boya': 'Desayuno Boyacense',
  'ham doble carne mayo cilantro': 'Hamburguesa doble carne con mayo de cilantro',
}

const getDisplayTitle = (name = '') => {
  const normalized = normalizeDbName(name)
  if (displayNameOverrides[normalized]) return displayNameOverrides[normalized]

  return String(name)
    .replace(/\.[^/.]+$/, '')
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .split(' ')
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
}

const getProductGroupKey = (item) => [
  item.id,
  item.title || '',
  Number(item.unitPrice || 0).toFixed(2),
].join('|')

export default function CajaPage() {
  const navigate = useNavigate()
  const { id: mesaId } = useParams()
  const [mesaState, setMesaState] = useState(null)
  const [ordenState, setOrdenState] = useState(null)
  const [orderItemsState, setOrderItemsState] = useState([])
  const [recetas, setRecetas] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [paymentError, setPaymentError] = useState('')
  const [selectedMethod, setSelectedMethod] = useState('efectivo')
  const [amountReceived, setAmountReceived] = useState('0')
  const [paymentConfirmed, setPaymentConfirmed] = useState(false)
  const [confirmedOrdenId, setConfirmedOrdenId] = useState(null)
  const [invoiceStatus, setInvoiceStatus] = useState(null)
  const [invoicePdfUrl, setInvoicePdfUrl] = useState(null)
  const [invoiceFacturaId, setInvoiceFacturaId] = useState(null)
  const [invoiceError, setInvoiceError] = useState('')
  const [invoicePolling, setInvoicePolling] = useState(false)
  const [isPaying, setIsPaying] = useState(false)
  const [mostrarDividir, setMostrarDividir] = useState(false)
  const [isDividedPayment, setIsDividedPayment] = useState(false)
  const [transferRef, setTransferRef] = useState('')
  const [boldAvailable, setBoldAvailable] = useState(false)
  const [boldPayment, setBoldPayment] = useState(null)
  const [boldTimedOut, setBoldTimedOut] = useState(false)

  useEffect(() => {
    const loadData = async () => {
      setLoading(true)
      setError('')
      setPaymentError('')
      setMesaState(null)
      setOrdenState(null)
      setOrderItemsState([])
      setRecetas([])

      try {
        const mesa = await getMesa(Number(mesaId))
        setMesaState(mesa)

        if (!mesa?.orden_id) {
          setError('Esta mesa no tiene una orden activa.')
          return
        }

        const [orden, recetasData] = await Promise.all([
          getOrden(mesa.orden_id),
          getRecetas(),
        ])

        setOrdenState(orden)
        setRecetas(recetasData)
        setOrderItemsState(
          orden.items.map((item) => ({
            id: item.receta_id,
            title: item.title || '',
            quantity: Number(item.cantidad),
            unitPrice: Number(item.precio_unitario),
            image: item.image || null,
          })),
        )
      } catch (err) {
        setError(err?.response?.data?.detail || err.message || 'No se pudo cargar la mesa o la orden.')
      } finally {
        setLoading(false)
      }
    }

    if (mesaId) {
      loadData()
    }
  }, [mesaId])

  useEffect(() => {
    getBoldTerminalAvailability().then((data) => setBoldAvailable(Boolean(data.pos_enabled && data.terminals?.length))).catch(() => setBoldAvailable(false))
  }, [])

  useEffect(() => {
    if (!boldPayment?.id || ['APROBADO', 'RECHAZADO'].includes(boldPayment.estado)) return undefined
    let cancelled = false
    const timeout = window.setTimeout(() => !cancelled && setBoldTimedOut(true), 90000)
    const poll = window.setInterval(async () => {
      try {
        const payment = await getPagoBoldTerminal(boldPayment.id)
        if (!cancelled) setBoldPayment(payment)
        if (payment.estado === 'APROBADO' && !cancelled) { setConfirmedOrdenId(ordenState?.orden_id); setPaymentConfirmed(true) }
      } catch { /* webhook status will be consulted again on next interval */ }
    }, 2500)
    return () => { cancelled = true; window.clearInterval(poll); window.clearTimeout(timeout) }
  }, [boldPayment?.id, boldPayment?.estado, ordenState?.orden_id])

  useEffect(() => {
    if (!confirmedOrdenId && ordenState?.orden_id && ['pagada', 'cerrada'].includes(ordenState.estado?.toLowerCase())) {
      setConfirmedOrdenId(ordenState.orden_id)
      setInvoiceStatus('pendiente')
      setInvoiceError('')
      setInvoiceFacturaId(null)
      setInvoicePdfUrl(null)
      setPaymentConfirmed(true)
    }
  }, [confirmedOrdenId, ordenState])

  const recetaNames = useMemo(
    () => recetas.reduce((acc, receta) => {
      acc[receta.id] = receta.nombre
      return acc
    }, {}),
    [recetas],
  )

  const orderItems = useMemo(
    () => {
      const grouped = new Map()

      orderItemsState.forEach((rawItem) => {
        const item = {
          ...rawItem,
          title: getDisplayTitle(rawItem.title || recetaNames[rawItem.id] || `Producto ${rawItem.id}`),
        }
        const key = getProductGroupKey(item)
        const existing = grouped.get(key)

        if (existing) {
          grouped.set(key, {
            ...existing,
            quantity: existing.quantity + item.quantity,
            image: existing.image || item.image,
          })
        } else {
          grouped.set(key, item)
        }
      })

      return Array.from(grouped.values())
    },
    [orderItemsState, recetaNames],
  )

  const productCount = useMemo(
    () => orderItems.reduce((sum, item) => sum + item.quantity, 0),
    [orderItems],
  )

  const subtotal = useMemo(
    () => orderItems.reduce((sum, item) => sum + item.unitPrice * item.quantity, 0),
    [orderItems],
  )

  const tax = useMemo(() => {
    if (ordenState?.total_neto != null && ordenState?.total_bruto != null) return Number(ordenState.total_neto - ordenState.total_bruto)
    return Number((subtotal * TAX_RATE).toFixed(2))
  }, [ordenState, subtotal])

  const total = useMemo(
    () => Number(ordenState?.total_neto ?? Number((subtotal + tax).toFixed(2))),
    [ordenState, subtotal, tax],
  )

  // Pre-fill monto recibido con el total cuando carga la orden
  useEffect(() => {
    if (total > 0 && (amountReceived === '0' || amountReceived === '')) {
      setAmountReceived(String(total))
    }
  }, [total])

  const amountReceivedNumber = Number(amountReceived) || 0

  const change = useMemo(
    () => (selectedMethod === 'efectivo' ? Math.max(0, Number((amountReceivedNumber - total).toFixed(2))) : 0),
    [amountReceivedNumber, selectedMethod, total],
  )

  // Billetes colombianos comunes superiores al total
  const quickAmounts = useMemo(() => {
    if (!total || total <= 0) return []
    const bills = [10000, 20000, 50000, 100000, 200000, 500000]
    const above = bills.filter((b) => b > total).slice(0, 3)
    return [total, ...above]
  }, [total])

  const paymentMethodLabel = useMemo(() => {
    if (isDividedPayment) return 'División de cuenta'
    return paymentMethods.find((m) => m.id === selectedMethod)?.label ?? selectedMethod
  }, [isDividedPayment, selectedMethod])

  const elapsed = formatElapsed(mesaState?.hora_apertura)

  const handleQuickAmount = (value) => setAmountReceived(String(value))

  const handleAmountReceivedChange = (event) => {
    const rawValue = event.target.value.replace(/\D/g, '')

    if (rawValue === '') {
      setAmountReceived('')
      return
    }

    // Mantiene un único cero cuando el usuario escribe ceros al inicio.
    setAmountReceived(rawValue.replace(/^0+(?=\d)/, ''))
  }

  const formatInvoiceStatus = (status) => {
    if (!status) return 'Sin estado'
    const normalized = String(status).toLowerCase()
    if (['pendiente', 'processing'].includes(normalized)) return 'Factura en proceso'
    if (['validated', 'aceptada', 'validada'].includes(normalized)) return 'Factura emitida'
    if (['rejected', 'rechazada'].includes(normalized)) return 'Factura rechazada'
    if (normalized === 'anulada') return 'Factura anulada'
    return status
  }

  const isFinalInvoiceStatus = (status) => {
    const normalized = String(status || '').toLowerCase()
    return ['validated', 'aceptada', 'validada', 'rejected', 'rechazada', 'anulada'].includes(normalized)
  }

  useEffect(() => {
    if (!paymentConfirmed || !confirmedOrdenId) return undefined

    let isCancelled = false
    let timerId = null
    let attempts = 0

    const pollFactura = async () => {
      if (isCancelled) return
      attempts += 1
      setInvoicePolling(true)

      try {
        const payload = await obtenerEstadoFacturaOrden(confirmedOrdenId)
        if (isCancelled) return

        setInvoiceStatus(payload.estado)
        setInvoiceFacturaId(payload.factura_id)
        setInvoicePdfUrl(payload.pdf_url)
        const normalizedEstado = String(payload.estado || '').toLowerCase()
        setInvoiceError(
          ['processing', 'rejected', 'rechazada'].includes(normalizedEstado)
            ? (payload.ultimo_error || (normalizedEstado === 'processing' ? 'Factus sigue procesando la factura con DIAN.' : 'Factus rechazó la factura.'))
            : '',
        )

        if (isFinalInvoiceStatus(payload.estado)) {
          return
        }

        if (attempts >= maxInvoicePollAttempts) {
          setInvoiceError('La factura quedó en proceso con Factus/DIAN. Puedes revisarla luego en Finanzas.')
          return
        }
      } catch (err) {
        if (isCancelled) return
        if (err?.response?.status === 404) {
          setInvoiceStatus('pendiente')
          setInvoiceError('Esperando a que se genere la factura...')
        } else {
          setInvoiceError(err?.response?.data?.detail || err.message || 'No se pudo consultar el estado de la factura.')
          return
        }

        if (attempts >= maxInvoicePollAttempts) {
          setInvoiceError('La factura quedó pendiente de consulta. Puedes revisarla luego en Finanzas.')
          return
        }
      } finally {
        if (!isCancelled) {
          setInvoicePolling(false)
        }
      }

      if (!isCancelled) {
        timerId = window.setTimeout(pollFactura, 2000)
      }
    }

    pollFactura()
    return () => {
      isCancelled = true
      if (timerId) {
        window.clearTimeout(timerId)
      }
    }
  }, [confirmedOrdenId, paymentConfirmed])

  const handleConfirmPayment = async () => {
    if (!ordenState?.orden_id) {
      setPaymentError('No se encontró orden activa para esta mesa.')
      return
    }

    if (selectedMethod === 'efectivo' && amountReceivedNumber < total) {
      setPaymentError('El monto recibido debe ser igual o mayor al total.')
      return
    }

    setPaymentError('')
    setIsPaying(true)

    try {
      if (selectedMethod.startsWith('tarjeta')) {
        if (!boldAvailable) throw new Error('El datáfono Bold no está disponible. Verifica que esté vinculado y conectado.')
        const payment = await crearPagoBoldTerminal({ orden_id: ordenState.orden_id, mesa_id: Number(mesaId), descripcion: `Mesa ${mesaState?.numero ?? mesaId} - ${productCount} productos` })
        setBoldPayment(payment)
        setBoldTimedOut(false)
        return
      }
      await registrarPago({
        orden_id: ordenState.orden_id,
        forma_pago: selectedMethod,
        monto: total,
        monto_recibido: selectedMethod === 'efectivo' ? amountReceivedNumber : undefined,
        referencia_datafono: selectedMethod.startsWith('tarjeta') ? `POS-${Date.now()}` : undefined,
        numero_comprobante: selectedMethod === 'nequi' ? (transferRef.trim() || `REF-${Date.now()}`) : undefined,
      })
      setConfirmedOrdenId(ordenState.orden_id)
      setInvoiceStatus('pendiente')
      setInvoiceError('')
      setInvoiceFacturaId(null)
      setInvoicePdfUrl(null)
      setPaymentConfirmed(true)
    } catch (err) {
      setPaymentError(err?.response?.data?.detail || err.message || 'No se pudo registrar el pago.')
    } finally {
      setIsPaying(false)
    }
  }

  const handleVerifyBold = async () => {
    if (!boldPayment?.id) return
    try {
      await verificarPagoBoldTerminal(boldPayment.id)
      setBoldPayment(await getPagoBoldTerminal(boldPayment.id))
      setBoldTimedOut(false)
    } catch (err) { setPaymentError(err?.response?.data?.detail || 'No se pudo verificar el pago en Bold.') }
  }

  return (
    <div className="caja-page">
      {paymentConfirmed && (
        <div className="caja-success-overlay">
          <div className="caja-success-card">
            <div className="caja-success-icon">✓</div>
            <h2>¡Pago confirmado!</h2>

            <div className="caja-success-details">
              <div className="caja-success-detail-row">
                <span>Mesa</span>
                <strong>Mesa {mesaState?.numero ?? mesaId}</strong>
              </div>
              <div className="caja-success-detail-row">
                <span>Total cobrado</span>
                <strong>{formatCOP(total)}</strong>
              </div>
              <div className="caja-success-detail-row">
                <span>Método</span>
                <strong>{paymentMethodLabel}</strong>
              </div>
              {change > 0 ? (
                <div className="caja-success-detail-row caja-success-detail-row--cambio">
                  <span>Cambio a entregar</span>
                  <strong className="caja-success-cambio">{formatCOP(change)}</strong>
                </div>
              ) : null}
              {mesaState?.mesero ? (
                <div className="caja-success-detail-row">
                  <span>Mesero</span>
                  <strong>{mesaState.mesero}</strong>
                </div>
              ) : null}
            </div>

            <div className="caja-success-invoice">
              {invoicePolling ? (
                <span className="caja-success-invoice-loading">Generando factura DIAN…</span>
              ) : invoicePdfUrl ? (
                <a href={invoicePdfUrl} target="_blank" rel="noreferrer" className="caja-success-invoice-btn">
                  Descargar factura PDF
                </a>
              ) : invoiceStatus ? (
                <span className="caja-success-invoice-status">{formatInvoiceStatus(invoiceStatus)}</span>
              ) : null}
              {invoiceError ? <span className="caja-success-invoice-error">{invoiceError}</span> : null}
            </div>

            <button
              type="button"
              className="caja-confirm-button"
              style={{ marginTop: 20 }}
              onClick={() => navigate('/mesas')}
            >
              Liberar mesa → Ir al mapa
            </button>
          </div>
        </div>
      )}

      <header className="caja-header">
        <div className="caja-header__left">
          <button type="button" className="caja-back-button" onClick={() => navigate('/mesas')}>
            ← Mesas
          </button>
          <div className="caja-header__title">
            <span className="caja-header__subtitle">Mesa {mesaState?.numero ?? mesaId}</span>
            <h1>Cierre de Cuenta</h1>
            <div className="caja-header__meta">
              {mesaState?.num_comensales ? <span>{mesaState.num_comensales} personas</span> : null}
              {mesaState?.mesero ? <span>{mesaState.mesero}</span> : null}
              {elapsed ? <span className="caja-header__elapsed">{elapsed} en mesa</span> : null}
            </div>
          </div>
        </div>

        <div className="caja-header__actions">
          <button
            type="button"
            className="caja-button-secondary"
            onClick={() => navigate(`/mesas/${mesaId}`)}
          >
            + Agregar productos
          </button>
          <button
            type="button"
            className="caja-button-primary"
            onClick={() => setMostrarDividir(true)}
          >
            ÷ Dividir cuenta
          </button>
        </div>
      </header>

      <div className="caja-content">
        <section className="caja-panel caja-panel--list">
          <div className="caja-panel__top">
            <div>
              <h2>Productos consumidos</h2>
              <p>{productCount} ítems en la orden</p>
            </div>
            <button
              type="button"
              className="caja-button-secondary"
              onClick={() => navigate(`/mesas/${mesaId}`)}
            >
              Agregar productos
            </button>
          </div>

          {loading ? (
            <div style={{ padding: 24, background: '#fff', borderRadius: 20, boxShadow: '0 18px 40px rgba(2,6,23,0.07)' }}>
              Cargando cuenta...
            </div>
          ) : error ? (
            <div style={{ padding: 24, background: '#fee2e2', borderRadius: 20, color: '#b91c1c' }}>{error}</div>
          ) : (
            <>
              <div className="caja-table">
                <div className="caja-table-row caja-table-row--head">
                  <span>PRODUCTO</span>
                  <span>CANT.</span>
                  <span>P. UNIT.</span>
                  <span>SUBTOTAL</span>
                </div>

                {orderItems.map((item) => (
                  <div key={`${item.id}-${item.title}`} className="caja-table-row">
                    <div className="caja-product-cell">
                      <div className="caja-product-image">
                        {item.image ? (
                          <img src={item.image} alt={item.title} />
                        ) : (
                          item.title?.charAt(0) || 'P'
                        )}
                      </div>
                      <span>{item.title}</span>
                    </div>
                    <span>{item.quantity}×</span>
                    <span>{formatCOP(item.unitPrice)}</span>
                    <span>{formatCOP(item.unitPrice * item.quantity)}</span>
                  </div>
                ))}
              </div>

              <div className="caja-panel__footer">
                <span>{productCount} productos</span>
                <strong>{formatCOP(subtotal)}</strong>
              </div>
            </>
          )}
        </section>

        <aside className="caja-summary-card">
          {mostrarDividir ? (
            <DividirCuenta
              orden_id={ordenState?.orden_id}
              monto_total={total}
              productos={orderItems.map((item) => ({
                id: item.id,
                nombre: item.title,
                cantidad: item.quantity,
                precio_unitario: item.unitPrice,
                foto_url: item.image || null,
              }))}
              onComplete={() => {
                setMostrarDividir(false)
                setIsDividedPayment(true)
                setConfirmedOrdenId(ordenState?.orden_id)
                setInvoiceStatus('pendiente')
                setInvoiceError('')
                setInvoiceFacturaId(null)
                setInvoicePdfUrl(null)
                setPaymentConfirmed(true)
              }}
              onCancel={() => setMostrarDividir(false)}
            />
          ) : (
            <>
              <div className="caja-section-title">RESUMEN</div>
              <div className="caja-summary-row">
                <span>Subtotal</span>
                <strong>{formatCOP(subtotal)}</strong>
              </div>
              <div className="caja-summary-row">
                <span>Impuestos (8%)</span>
                <strong>{formatCOP(tax)}</strong>
              </div>
              <div className="caja-summary-row caja-summary-row--total">
                <span>Total</span>
                <strong>{formatCOP(total)}</strong>
              </div>

              <div className="caja-section-title">MÉTODO DE PAGO</div>
              <div className="caja-method-grid">
                {paymentMethods.map((method) => (
                  <button
                    key={method.id}
                    type="button"
                    className={`caja-method-card ${selectedMethod === method.id ? 'active' : ''}`}
                    onClick={() => setSelectedMethod(method.id)}
                    disabled={method.id.startsWith('tarjeta') && !boldAvailable}
                  >
                    <span className="caja-method-icon">{method.icon}</span>
                    <span>{method.label}</span>
                  </button>
                ))}
              </div>

              {selectedMethod === 'efectivo' ? (
                <>
                  <div className="caja-section-title">MONTO RECIBIDO</div>
                  <div className="caja-input-group">
                    <span className="caja-input-prefix">$</span>
                    <input
                      type="text"
                      className="caja-input"
                      value={amountReceived === '' ? '' : formatCOPNumber(amountReceived)}
                      inputMode="numeric"
                      autoComplete="off"
                      aria-label="Monto recibido"
                      onFocus={(event) => event.currentTarget.select()}
                      onChange={handleAmountReceivedChange}
                    />
                  </div>
                  <div className="caja-quick-buttons">
                    {quickAmounts.map((amount, index) => (
                      <button
                        key={`quick-${index}-${amount}`}
                        type="button"
                        className={`caja-quick-button ${amount === amountReceivedNumber ? 'active' : ''}`}
                        onClick={() => handleQuickAmount(amount)}
                      >
                        {index === 0 ? 'Exacto' : formatCOP(amount)}
                      </button>
                    ))}
                  </div>
                  <div className="caja-change-card">
                    <span>Cambio a entregar</span>
                    <strong className={change > 0 ? 'caja-change-positive' : ''}>{formatCOP(change)}</strong>
                  </div>
                </>
              ) : selectedMethod === 'nequi' ? (
                <>
                  <div className="caja-section-title">REFERENCIA DE PAGO</div>
                  <div className="caja-input-group" style={{ marginBottom: 8 }}>
                    <input
                      type="text"
                      className="caja-input"
                      style={{ fontSize: '1rem', paddingLeft: '1rem' }}
                      value={transferRef}
                      placeholder="Número de aprobación (opcional)"
                      autoComplete="off"
                      onChange={(e) => setTransferRef(e.target.value)}
                    />
                  </div>
                  <p style={{ margin: '0 0 14px', color: '#596675', fontSize: 13 }}>
                    Verifica que el cliente ya realizó la transferencia antes de confirmar.
                  </p>
                </>
              ) : (
                <p style={{ margin: '0 0 14px', padding: '12px 16px', borderRadius: 12, background: '#f7efd9', color: '#73551d', fontSize: 13 }}>
                  Se registrará el cobro por terminal de tarjeta Bold. Asegúrate de que el datáfono esté disponible.
                </p>
              )}

              {boldPayment ? (
                <div className={`caja-bold-status caja-bold-status--${boldPayment.estado.toLowerCase()}`}>
                  <strong>{boldPayment.estado === 'RECHAZADO' ? 'Pago rechazado' : boldPayment.estado === 'APROBADO' ? 'Pago exitoso' : 'Esperando pago en datáfono…'}</strong>
                  {boldPayment.ultimo_error ? <div>{boldPayment.ultimo_error}</div> : null}
                  {boldTimedOut ? <button type="button" className="caja-bold-verify" onClick={handleVerifyBold}>Verificar estado manualmente</button> : null}
                </div>
              ) : null}

              {paymentError ? (
                <div style={{ marginBottom: 14, padding: '10px 14px', borderRadius: 12, background: '#fee2e2', color: '#b91c1c', fontWeight: 700 }}>{paymentError}</div>
              ) : null}

              <button
                type="button"
                onClick={handleConfirmPayment}
                className="caja-confirm-button"
                disabled={isPaying || !!error || orderItems.length === 0 || (selectedMethod.startsWith('tarjeta') && (!boldAvailable || (boldPayment && !['RECHAZADO', 'APROBADO'].includes(boldPayment.estado))))}
              >
                {isPaying ? 'Procesando...' : boldPayment && !['RECHAZADO', 'APROBADO'].includes(boldPayment.estado) ? 'Esperando pago en datáfono...' : 'Realizar pago'}
              </button>
            </>
          )}
        </aside>
      </div>
    </div>
  )
}
