import { useMemo, useState } from 'react'
import apiClient from '../../../shared/api/apiClient'
import { formatCOP } from '../../../shared/utils/currency'
import './DividirCuenta.css'

const FORMAS_PAGO = [
  { id: 'efectivo', label: 'Efectivo', icon: '$' },
  { id: 'tarjeta_debito', label: 'Tarjeta', icon: 'CARD' },
  { id: 'nequi', label: 'Transferencia', icon: 'REF' },
]

const getItemKey = (item) => [
  item.id,
  item.nombre || '',
  Number(item.precio_unitario || 0).toFixed(2),
].join('|')

const roundMoney = (value) => Number(Number(value || 0).toFixed(2))

const DividirCuenta = ({
  orden_id,
  monto_total,
  productos = [],
  onComplete,
  onCancel,
}) => {
  const [paso, setPaso] = useState('seleccionar')
  const [modoDivision, setModoDivision] = useState('igual')
  const [numeroPersonas, setNumeroPersonas] = useState(2)
  const [division, setDivision] = useState(null)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')
  const [pagosRegistrados, setPagosRegistrados] = useState(new Map())
  const [personasExpandidas, setPersonasExpandidas] = useState(new Set([1]))
  const [asignaciones, setAsignaciones] = useState({})

  const productosConKey = useMemo(
    () => {
      const grouped = new Map()

      productos.forEach((item) => {
        const key = getItemKey(item)
        const existing = grouped.get(key)

        if (existing) {
          grouped.set(key, {
            ...existing,
            cantidad: Number(existing.cantidad) + Number(item.cantidad),
            foto_url: existing.foto_url || item.foto_url,
          })
        } else {
          grouped.set(key, {
            ...item,
            key,
            cantidad: Number(item.cantidad),
            precio_unitario: Number(item.precio_unitario),
          })
        }
      })

      return Array.from(grouped.values())
    },
    [productos],
  )

  const subtotalProductos = useMemo(
    () => productosConKey.reduce((sum, item) => sum + Number(item.precio_unitario) * Number(item.cantidad), 0),
    [productosConKey],
  )

  const personas = useMemo(
    () => Array.from({ length: numeroPersonas }, (_, index) => index + 1),
    [numeroPersonas],
  )

  const cantidadesAsignadas = useMemo(() => {
    return productosConKey.reduce((acc, item) => {
      acc[item.key] = personas.reduce(
        (sum, persona) => sum + Number(asignaciones[persona]?.[item.key] || 0),
        0,
      )
      return acc
    }, {})
  }, [asignaciones, personas, productosConKey])

  const cantidadesPendientes = useMemo(() => {
    return productosConKey.reduce((acc, item) => {
      acc[item.key] = Math.max(0, Number(item.cantidad) - Number(cantidadesAsignadas[item.key] || 0))
      return acc
    }, {})
  }, [cantidadesAsignadas, productosConKey])

  const resumenPersonas = useMemo(() => {
    const resumen = personas.map((numero) => {
      const items = productosConKey
        .map((item) => {
          const cantidad = Number(asignaciones[numero]?.[item.key] || 0)
          return {
            key: item.key,
            nombre: item.nombre,
            foto_url: item.foto_url,
            cantidad,
            subtotal: cantidad * Number(item.precio_unitario),
          }
        })
        .filter((item) => item.cantidad > 0)

      return {
        numero_persona: numero,
        items,
        subtotal: items.reduce((sum, item) => sum + item.subtotal, 0),
        monto: 0,
      }
    })

    if (modoDivision !== 'productos' || subtotalProductos <= 0) {
      return resumen.map((persona) => ({
        ...persona,
        monto: roundMoney(Number(monto_total) / numeroPersonas),
      }))
    }

    let acumulado = 0
    return resumen.map((persona, index) => {
      const esUltima = index === resumen.length - 1
      const monto = esUltima
        ? roundMoney(Number(monto_total) - acumulado)
        : roundMoney((persona.subtotal / subtotalProductos) * Number(monto_total))
      acumulado += monto
      return { ...persona, monto }
    })
  }, [asignaciones, modoDivision, monto_total, numeroPersonas, personas, productosConKey, subtotalProductos])

  const totalAsignado = useMemo(
    () => productosConKey.reduce((sum, item) => sum + Number(cantidadesAsignadas[item.key] || 0), 0),
    [cantidadesAsignadas, productosConKey],
  )

  const totalProductos = useMemo(
    () => productosConKey.reduce((sum, item) => sum + Number(item.cantidad), 0),
    [productosConKey],
  )

  const productosSinAsignar = totalProductos - totalAsignado
  const todosAsignados = modoDivision === 'igual' || (productosSinAsignar === 0 && resumenPersonas.every((p) => p.subtotal > 0))

  const cambiarNumeroPersonas = (nuevoNumero) => {
    const numero = Math.min(20, Math.max(2, nuevoNumero))
    setNumeroPersonas(numero)
    setPersonasExpandidas(new Set([1]))
    setAsignaciones((actuales) => {
      const siguientes = {}
      for (let persona = 1; persona <= numero; persona += 1) {
        siguientes[persona] = actuales[persona] || {}
      }
      return siguientes
    })
  }

  const cambiarCantidad = (persona, item, delta) => {
    const actual = Number(asignaciones[persona]?.[item.key] || 0)
    const asignadoOtrasPersonas = Number(cantidadesAsignadas[item.key] || 0) - actual
    const maximo = Number(item.cantidad) - asignadoOtrasPersonas
    const siguienteCantidad = Math.min(maximo, Math.max(0, actual + delta))

    setAsignaciones((prev) => ({
      ...prev,
      [persona]: {
        ...(prev[persona] || {}),
        [item.key]: siguienteCantidad,
      },
    }))
  }

  const crearDivision = async () => {
    if (!orden_id) {
      setError('No se encontro una orden activa para dividir.')
      return
    }

    if (!todosAsignados) {
      setError('Asigna todos los productos y deja al menos un producto por persona.')
      return
    }

    setCargando(true)
    setError('')

    try {
      const payload = {
        orden_id,
        numero_personas: numeroPersonas,
        monto_total,
      }

      if (modoDivision === 'productos') {
        payload.montos_personas = resumenPersonas.map((persona) => persona.monto)
      }

      const response = await apiClient.post('/pagos-divididos/crear', payload)
      setDivision(response.data)
      setPaso('pagos')
      setPersonasExpandidas(new Set([1]))
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Error al crear division')
    } finally {
      setCargando(false)
    }
  }

  const registrarPago = async (persona, formaPago, montoRecibido, referencia) => {
    setCargando(true)
    setError('')

    try {
      const payload = {
        numero_persona: persona.numero_persona,
        forma_pago: formaPago,
      }

      if (formaPago === 'efectivo') {
        payload.monto_recibido = montoRecibido
      } else if (formaPago.includes('tarjeta')) {
        payload.referencia_datafono = referencia || `POS-${Date.now()}`
      } else {
        payload.numero_comprobante = referencia || `REF-${Date.now()}`
      }

      const response = await apiClient.post(`/pagos-divididos/${division.id}/pagar`, payload)
      const resultado = response.data
      const nuevosPagos = new Map(pagosRegistrados)

      nuevosPagos.set(persona.numero_persona, {
        ...persona,
        pagado: true,
        forma_pago: formaPago,
        monto_recibido: montoRecibido,
        cambio_entregado: resultado.cambio_entregado,
        pagado_at: resultado.pagado_at,
      })

      setPagosRegistrados(nuevosPagos)

      if (resultado.completado_division) {
        setTimeout(() => onComplete?.(), 1000)
      }
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Error al registrar pago')
    } finally {
      setCargando(false)
    }
  }

  const togglePersona = (numero) => {
    const nuevas = new Set(personasExpandidas)
    if (nuevas.has(numero)) {
      nuevas.delete(numero)
    } else {
      nuevas.add(numero)
    }
    setPersonasExpandidas(nuevas)
  }

  const renderAsignadorProductos = () => (
    <div className="asignador-productos-panel">
      <div className="asignador-resumen-panel">
        <span>{totalAsignado} de {totalProductos} productos asignados</span>
        <strong>{productosSinAsignar === 0 ? 'Completo' : `${productosSinAsignar} pendientes`}</strong>
      </div>

      {resumenPersonas.map((persona) => (
        <div key={persona.numero_persona} className="asignador-persona-panel">
          <div className="asignador-persona-header">
            <strong>Persona {persona.numero_persona}</strong>
            <span>{formatCOP(persona.monto)}</span>
          </div>

          {productosConKey.map((item) => {
            const cantidad = Number(asignaciones[persona.numero_persona]?.[item.key] || 0)
            const pendientes = Number(cantidadesPendientes[item.key] || 0)
            const puedeSumar = pendientes > 0

            return (
              <div key={item.key} className="asignador-item-panel">
                <div className="asignador-producto-info">
                  <div className="asignador-producto-imagen">
                    {item.foto_url ? (
                      <img src={item.foto_url} alt={item.nombre} />
                    ) : (
                      item.nombre?.charAt(0) || 'P'
                    )}
                  </div>
                  <div>
                    <span>{item.nombre}</span>
                    <small>{formatCOP(item.precio_unitario)} c/u</small>
                  </div>
                </div>
                <div className="contador-item-panel">
                  <button type="button" onClick={() => cambiarCantidad(persona.numero_persona, item, -1)} disabled={cantidad === 0}>-</button>
                  <span>{cantidad}</span>
                  <button type="button" onClick={() => cambiarCantidad(persona.numero_persona, item, 1)} disabled={!puedeSumar}>+</button>
                </div>
              </div>
            )
          })}
        </div>
      ))}
    </div>
  )

  const renderSeleccionar = () => (
    <div className="dividir-panel-contenido">
      <div className="dividir-panel-header">
        <h3>Dividir cuenta</h3>
        <button className="btn-cerrar-panel" onClick={onCancel}>x</button>
      </div>

      <div className="modo-division-panel">
        <button
          type="button"
          className={modoDivision === 'igual' ? 'activo' : ''}
          onClick={() => setModoDivision('igual')}
        >
          Partes iguales
        </button>
        <button
          type="button"
          className={modoDivision === 'productos' ? 'activo' : ''}
          onClick={() => setModoDivision('productos')}
          disabled={productosConKey.length === 0}
        >
          Por productos
        </button>
      </div>

      <div className="selector-personas-panel">
        <button className="btn-menos-panel" onClick={() => cambiarNumeroPersonas(numeroPersonas - 1)}>-</button>
        <div className="numero-personas-panel">{numeroPersonas}</div>
        <button className="btn-mas-panel" onClick={() => cambiarNumeroPersonas(numeroPersonas + 1)}>+</button>
      </div>

      <p className="texto-personas-panel">personas</p>

      <div className="opciones-rapidas-panel">
        {[2, 3, 4, 5].map((n) => (
          <button
            key={n}
            className={`btn-opcion-panel ${numeroPersonas === n ? 'activo' : ''}`}
            onClick={() => cambiarNumeroPersonas(n)}
          >
            {n}
          </button>
        ))}
      </div>

      {modoDivision === 'productos' ? renderAsignadorProductos() : (
        <div className="resumen-precio-panel">
          <span className="label-panel">Cada persona paga</span>
          <span className="precio-panel">{formatCOP(Number(monto_total) / numeroPersonas)}</span>
        </div>
      )}

      <button
        className="btn-aplicar-division-panel"
        onClick={crearDivision}
        disabled={cargando || !todosAsignados}
      >
        {cargando ? 'Creando...' : 'Aplicar division'}
      </button>
    </div>
  )

  const renderPagos = () => {
    const personasDivision = division.personas.map((persona) => ({
      ...persona,
      detalle: resumenPersonas.find((resumen) => resumen.numero_persona === persona.numero_persona)?.items || [],
    }))
    const personasPagadas = pagosRegistrados.size
    const pagosRestantes = division.numero_personas - personasPagadas
    const montoPagado = personasDivision.reduce((sum, persona) => (
      pagosRegistrados.has(persona.numero_persona) ? sum + Number(persona.monto) : sum
    ), 0)

    return (
      <div className="dividir-panel-pagos">
        <div className="dividir-panel-header">
          <h3>Dividir cuenta</h3>
          <button className="btn-cerrar-panel" onClick={onCancel}>x</button>
        </div>

        <div className="encabezado-pagos-panel">
          <span className="contador-pagos-panel">{personasPagadas} de {division.numero_personas} pagaron</span>
          <span>{formatCOP(montoPagado)} / {formatCOP(monto_total)}</span>
        </div>

        <div className="barra-progreso-pagos-panel">
          <div className="relleno-panel" style={{ width: `${(personasPagadas / division.numero_personas) * 100}%` }} />
        </div>

        <div className="lista-personas-panel">
          {personasDivision.map((persona) => {
            const pagado = pagosRegistrados.get(persona.numero_persona) || persona
            const expandida = personasExpandidas.has(persona.numero_persona)

            return (
              <div key={persona.numero_persona} className="persona-card-panel">
                <div
                  className={`persona-header-panel ${pagado.pagado ? 'pagado' : ''}`}
                  onClick={() => !pagado.pagado && togglePersona(persona.numero_persona)}
                >
                  <div className="persona-info-panel">
                    <div className="persona-avatar-panel">{pagado.pagado ? 'OK' : persona.numero_persona}</div>
                    <div>
                      <div className="persona-nombre-panel">Persona {persona.numero_persona}</div>
                      <div className="persona-deuda-panel">Debe {formatCOP(persona.monto)}</div>
                    </div>
                  </div>
                  <div className="persona-monto-panel">
                    <span>{formatCOP(persona.monto)}</span>
                    {!pagado.pagado && <span className="expand-icon-panel">{expandida ? '^' : 'v'}</span>}
                  </div>
                </div>

                {persona.detalle.length > 0 && (
                  <div className="persona-detalle-productos">
                    {persona.detalle.map((item) => (
                      <span key={item.key}>{item.cantidad}x {item.nombre}</span>
                    ))}
                  </div>
                )}

                {expandida && !pagado.pagado && (
                  <FormaPagoPersona
                    persona={persona}
                    onPagar={(formaPago, montoRecibido, referencia) =>
                      registrarPago(persona, formaPago, montoRecibido, referencia)
                    }
                    cargando={cargando}
                  />
                )}
              </div>
            )
          })}
        </div>

        {pagosRestantes > 0 && (
          <div className="faltan-pagos-panel">
            Faltan {pagosRestantes} pagos
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="dividir-cuenta-panel">
      {error && <div className="alerta-error-panel">{error}</div>}
      {paso === 'seleccionar' && renderSeleccionar()}
      {paso === 'pagos' && renderPagos()}
    </div>
  )
}

const FormaPagoPersona = ({
  persona,
  onPagar,
  cargando,
}) => {
  const [formaPago, setFormaPago] = useState('efectivo')
  const [montoRecibido, setMontoRecibido] = useState(String(Math.ceil(Number(persona.monto) || 0)))
  const [referencia, setReferencia] = useState('')
  const montoRecibidoNumero = Number(montoRecibido || 0)

  const quickAmounts = [
    Math.ceil(Number(persona.monto)),
    Math.ceil(Number(persona.monto) + 10000),
    Math.ceil(Number(persona.monto) + 20000),
  ]

  const cambiarMontoRecibido = (value) => {
    const soloNumeros = value.replace(/\D/g, '')
    setMontoRecibido(soloNumeros.replace(/^0+(?=\d)/, ''))
  }

  return (
    <div className="forma-pago-section-panel">
      <div className="label-forma-panel">Metodo de pago</div>

      <div className="opciones-forma-panel">
        {FORMAS_PAGO.map((fp) => (
          <button
            key={fp.id}
            className={`btn-forma-pago-panel ${formaPago === fp.id ? 'activo' : ''}`}
            onClick={() => setFormaPago(fp.id)}
          >
            <span className="icon-forma-panel">{fp.icon}</span>
            <span className="label-forma-pago-panel">{fp.label}</span>
          </button>
        ))}
      </div>

      {formaPago === 'efectivo' ? (
        <div className="input-efectivo-panel">
          <label>Monto recibido</label>
          <input
            type="text"
            inputMode="numeric"
            value={montoRecibido}
            onChange={(e) => cambiarMontoRecibido(e.target.value)}
            onFocus={() => montoRecibido === '0' && setMontoRecibido('')}
          />
          <small>Cambio: {formatCOP(Math.max(0, montoRecibidoNumero - Number(persona.monto)))}</small>

          <div className="quick-amounts-panel">
            {quickAmounts.map((amount) => (
              <button
                key={amount}
                className="quick-amount-button"
                onClick={() => setMontoRecibido(String(amount))}
              >
                {formatCOP(amount)}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="input-efectivo-panel">
          <label>{formaPago === 'tarjeta_debito' ? 'Referencia datafono' : 'Numero comprobante'}</label>
          <input
            type="text"
            value={referencia}
            onChange={(e) => setReferencia(e.target.value)}
            placeholder={formaPago === 'tarjeta_debito' ? 'POS-123' : 'REF-123'}
          />
        </div>
      )}

      <button
        className="btn-cobrar-panel"
        onClick={() => onPagar(formaPago, montoRecibidoNumero, referencia)}
        disabled={cargando || (formaPago === 'efectivo' && montoRecibidoNumero < Number(persona.monto))}
      >
        Cobrar {formatCOP(persona.monto)}
      </button>
    </div>
  )
}

export default DividirCuenta
