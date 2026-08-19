import { useState, useEffect, useRef, useMemo } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useMesas } from '../hooks/useMesas'
import { useAbrirMesa } from '../hooks/useAbrirMesa'
import { useAuth } from '../../auth/hooks/useAuth'
import { formatCOP } from '../../../shared/utils/currency'

const tableLayouts = {
  1: { zone: 'principal' }, 2: { zone: 'principal' }, 3: { zone: 'principal' },
  4: { zone: 'principal' }, 5: { zone: 'principal' }, 6: { zone: 'terraza' },
  7: { zone: 'terraza' }, 8: { zone: 'bar' },
}

const zoneConfig = {
  principal: {
    label: 'Salon Principal',
    className: 'zone-principal',
  },
  terraza: {
    label: 'Terraza',
    className: 'zone-terraza',
  },
  bar: {
    label: 'Bar',
    className: 'zone-bar',
  },
}

function normalizeStatus(mesa) {
  const estado = (mesa?.estado || '').toLowerCase()
  if (estado.includes('ocup') || mesa?.orden_id) return 'ocupada'
  if (estado.includes('reserv')) return 'reservada'
  return 'libre'
}

function getZoneKey(mesa) {
  const rawZone = (mesa?.zona || '').toLowerCase()
  if (rawZone.includes('terra')) return 'terraza'
  if (rawZone.includes('bar')) return 'bar'
  return tableLayouts[Number(mesa?.numero)]?.zone || 'principal'
}

function getStatusLabel(status) {
  if (status === 'ocupada') return 'Ocupada'
  if (status === 'reservada') return 'Reservada'
  return 'Libre'
}

function formatElapsed(horaApertura) {
  if (!horaApertura) return null
  const diff = Math.floor((Date.now() - new Date(horaApertura).getTime()) / 1000)
  if (diff < 60) return `${diff}s`
  const m = Math.floor(diff / 60)
  if (m < 60) return `${m}min`
  return `${Math.floor(m / 60)}h ${m % 60}min`
}

export default function MesasPage() {
  const [selectedMesa, setSelectedMesa] = useState(null)
  const [numComensales, setNumComensales] = useState(1)
  const [notas, setNotas] = useState('')
  const [time, setTime] = useState(new Date())
  const [tableSearch, setTableSearch] = useState('')
  const [highlightedMesa, setHighlightedMesa] = useState(null)
  const [statusFilter, setStatusFilter] = useState('Todas')
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { user, logout } = useAuth()

  const modalRef = useRef(null)
  const lastActiveRef = useRef(null)

  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(id)
  }, [])

  const { data: mesas = [], isLoading, isError, error } = useMesas()
  const abrirMesaMutation = useAbrirMesa()
  const meseroNombre = user?.nombre || user?.username || user?.email || 'Mesero'
  const capacidadSeleccionada = Math.max(1, Number.parseInt(selectedMesa?.capacidad, 10) || 1)

  const stats = useMemo(() => {
    const libres = mesas.filter((mesa) => normalizeStatus(mesa) === 'libre').length
    const ocupadas = mesas.filter((mesa) => normalizeStatus(mesa) === 'ocupada').length
    const reservadas = mesas.filter((mesa) => normalizeStatus(mesa) === 'reservada').length
    return { libres, ocupadas, reservadas, total: mesas.length }
  }, [mesas])

  const mesasByZone = useMemo(() => {
    return mesas.reduce((acc, mesa, index) => {
      const zone = getZoneKey(mesa)
      const layout = tableLayouts[Number(mesa.numero)] || { zone }
      acc[zone] = acc[zone] || []
      acc[zone].push({ ...mesa, layout })
      return acc
    }, {})
  }, [mesas])

  const zoneStats = useMemo(() => {
    return Object.keys(zoneConfig).reduce((acc, zone) => {
      const zoneTables = mesas.filter((mesa) => getZoneKey(mesa) === zone)
      acc[zone] = {
        total: zoneTables.length,
        ocupadas: zoneTables.filter((mesa) => normalizeStatus(mesa) === 'ocupada').length,
      }
      return acc
    }, {})
  }, [mesas])

  const handleAbrir = (mesa) => {
    lastActiveRef.current = document.activeElement
    setSelectedMesa(mesa)
    setNumComensales(1)
    setNotas('')
  }

  const handleMesaAction = (mesa) => {
    if (normalizeStatus(mesa) === 'libre') {
      handleAbrir(mesa)
      return
    }
    navigate(`/mesas/${mesa.id}`)
  }

  useEffect(() => {
    if (!selectedMesa) return

    const node = modalRef.current
    const focusable = node?.querySelectorAll('button, [href], input, textarea, select, [tabindex]:not([tabindex="-1"])') || []
    focusable[0]?.focus()

    function handleKey(e) {
      if (e.key === 'Escape') {
        setSelectedMesa(null)
        return
      }
      if (e.key !== 'Tab') return

      const focusableEls = Array.from(focusable)
      if (focusableEls.length === 0) return
      const idx = focusableEls.indexOf(document.activeElement)
      if (e.shiftKey && idx === 0) {
        focusableEls[focusableEls.length - 1].focus()
        e.preventDefault()
      }
      if (!e.shiftKey && idx === focusableEls.length - 1) {
        focusableEls[0].focus()
        e.preventDefault()
      }
    }

    document.addEventListener('keydown', handleKey)
    return () => {
      document.removeEventListener('keydown', handleKey)
      try { lastActiveRef.current?.focus() } catch (err) {}
    }
  }, [selectedMesa])

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (!selectedMesa) return

    await abrirMesaMutation.mutateAsync({
      mesaId: selectedMesa.id,
      data: { num_comensales: numComensales, notas },
    })

    await queryClient.invalidateQueries(['mesas'])
    setSelectedMesa(null)
    navigate(`/mesas/${selectedMesa.id}`)
  }

  return (
    <div className="restaurant-map-page">
      <header className="restaurant-map-header">
        <div className="restaurant-brand">
          <div className="restaurant-brand__mark">R</div>
          <div>
            <strong>RestoPOS</strong>
            <span>Mapa del restaurante</span>
          </div>
        </div>

        <div className="restaurant-header-info">
          <span className="restaurant-stat restaurant-stat--free">{stats.libres} libres</span>
          <span className="restaurant-stat restaurant-stat--busy">{stats.ocupadas} ocupadas</span>
          <span className="restaurant-user">
            <small>Mesero a cargo</small>
            <strong>{meseroNombre}</strong>
          </span>
          <span className="restaurant-time">
            <small>Hora</small>
            <strong>{time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</strong>
          </span>
        </div>
        <nav className="restaurant-header-actions" aria-label="Acciones principales">
          <div className="restaurant-header-actions__secondary">
            <button type="button" className="restaurant-header-button" onClick={() => navigate('/inventario')}>Inventario</button>
            <button type="button" className="restaurant-header-button" onClick={() => navigate('/recetario')}>Recetario</button>
            <button type="button" className="restaurant-header-button" onClick={() => navigate('/cierre-caja')}>Cierre de caja</button>
            {['cajero', 'administrador'].includes(user?.rol) ? <button type="button" className="restaurant-header-button" onClick={() => navigate('/finanzas')}>Finanzas</button> : null}
          </div>
          <details className="restaurant-header-actions__more">
            <summary aria-label="Más acciones">•••</summary>
            <div>
              <button type="button" onClick={() => navigate('/inventario')}>Inventario</button>
              <button type="button" onClick={() => navigate('/recetario')}>Recetario</button>
              <button type="button" onClick={() => navigate('/cierre-caja')}>Cierre de caja</button>
              {['cajero', 'administrador'].includes(user?.rol) ? <button type="button" onClick={() => navigate('/finanzas')}>Finanzas</button> : null}
            </div>
          </details>
          {['cajero', 'administrador'].includes(user?.rol) ? <button type="button" className="restaurant-header-button restaurant-header-button--bold" onClick={() => navigate('/bold-prueba')}>Pago Bold prueba</button> : null}
          <button type="button" className="restaurant-header-button restaurant-header-button--danger" onClick={() => logout()}>Cerrar sesión</button>
        </nav>
      </header>

      <main className="restaurant-map-shell">
        <section className="restaurant-floor" aria-label="Mapa de mesas">
          {isError ? (
            <div className="restaurant-empty-state">Error: {error?.message || 'No se pudo cargar las mesas'}</div>
          ) : null}

          {isLoading ? (
            <div className="restaurant-empty-state">Cargando mesas...</div>
          ) : null}

          {!isLoading && mesas.length === 0 ? (
            <div className="restaurant-empty-state">No hay mesas configuradas.</div>
          ) : null}

          {!isLoading && mesas.length > 0 ? (
            <>
              {Object.entries(zoneConfig).map(([zoneKey, zone]) => (
                <div key={zoneKey} className={`floor-zone ${zone.className}`}>
                  <div className="floor-zone__label">{zone.label}</div>

                  <div className="floor-zone__tables">
                  {(mesasByZone[zoneKey] || []).map((mesa) => {
                    const status = normalizeStatus(mesa)
                    const elapsed = status === 'ocupada' ? formatElapsed(mesa.hora_apertura) : null
                    const total = status === 'ocupada' ? Number(mesa.total_neto) : 0
                    const guests = status === 'ocupada' ? mesa.num_comensales : null
                    return (
                      <button
                        key={mesa.id}
                        type="button"
                        className={`floor-table floor-table--${status} ${highlightedMesa === mesa.id ? 'is-highlighted' : ''}`}
                        onClick={() => handleMesaAction(mesa)}
                        onMouseEnter={() => setHighlightedMesa(mesa.id)}
                        onMouseLeave={() => setHighlightedMesa(null)}
                      >
                        <div className="floor-table__top">
                          <span className="floor-table__dot" />
                          {elapsed ? <span className="floor-table__elapsed">{elapsed}</span> : null}
                        </div>
                        <strong>Mesa {mesa.numero}</strong>
                        <small>
                          {guests ? `${guests} pers.` : `Cap. ${mesa.capacidad ?? '?'}`}
                        </small>
                        {total > 0 ? <span className="floor-table__total">{formatCOP(total)}</span> : null}
                        <b>{getStatusLabel(status)}</b>
                      </button>
                    )
                  })}
                  {(mesasByZone[zoneKey] || []).length === 0 ? (
                    <div className="floor-zone__empty"><span>Sin mesas configuradas</span><button type="button" onClick={() => navigate('/mesas/nueva')}>+ Agregar mesa</button></div>
                  ) : null}
                  </div>
                </div>
              ))}

              <div className="floor-entrance">Entrada principal</div>
            </>
          ) : null}
        </section>

        <aside className="restaurant-sidebar">
          <section className="sidebar-block">
            <h2>Estado General</h2>
            <div className="occupancy-summary">
            <div className="occupancy-ring" style={{ '--busy': `${stats.total ? (stats.ocupadas / stats.total) * 360 : 0}deg` }}>
              <div>
                <strong>{stats.ocupadas}</strong>
                <span>ocupadas</span>
              </div>
            </div>
            <div className="occupancy-legend"><span><i className="is-free" />Libres {stats.libres}</span><span><i className="is-busy" />Ocupadas {stats.ocupadas}</span></div>
            </div>
            <p><strong>{stats.total}</strong> mesas en total</p>
          </section>

          <section className="sidebar-zones">
            {Object.entries(zoneConfig).map(([zoneKey, zone]) => (
              <div key={zoneKey} className={`sidebar-zone ${zone.className}`}>
                <span />
                <div>
                  <strong>{zone.label}</strong>
                  <small><b>{zoneStats[zoneKey]?.ocupadas || 0}/{zoneStats[zoneKey]?.total || 0}</b> ocupadas</small>
                </div>
              </div>
            ))}
          </section>

          <section className="sidebar-table-list">
            <h2>Mesas</h2>
            <input className="sidebar-table-search" type="search" value={tableSearch} onChange={(event) => setTableSearch(event.target.value)} placeholder="Buscar mesa…" aria-label="Buscar mesa" />
            <div className="sidebar-filter" role="group" aria-label="Filtrar por estado">
              {['Todas', 'Libre', 'Ocupada'].map((f) => (
                <button key={f} type="button" className={`sidebar-filter__btn${statusFilter === f ? ' active' : ''}`} onClick={() => setStatusFilter(f)}>
                  {f}
                </button>
              ))}
            </div>
            <div className="sidebar-table-list__scroll">
              {mesas
                .filter((mesa) => String(mesa.numero).includes(tableSearch.trim()))
                .filter((mesa) => {
                  if (statusFilter === 'Todas') return true
                  return normalizeStatus(mesa) === statusFilter.toLowerCase()
                })
                .sort((a, b) => {
                  const sa = normalizeStatus(a)
                  const sb = normalizeStatus(b)
                  if (sa === 'ocupada' && sb !== 'ocupada') return -1
                  if (sb === 'ocupada' && sa !== 'ocupada') return 1
                  return Number(a.numero) - Number(b.numero)
                })
                .map((mesa) => {
                  const status = normalizeStatus(mesa)
                  const elapsed = status === 'ocupada' ? formatElapsed(mesa.hora_apertura) : null
                  const total = status === 'ocupada' ? Number(mesa.total_neto) : 0
                  return (
                    <button key={mesa.id} type="button" className={`sidebar-table-row${highlightedMesa === mesa.id ? ' is-highlighted' : ''}`} onClick={() => handleMesaAction(mesa)} onMouseEnter={() => setHighlightedMesa(mesa.id)} onMouseLeave={() => setHighlightedMesa(null)}>
                      <span className={`sidebar-table-row__dot sidebar-table-row__dot--${status}`} />
                      <span className="sidebar-table-row__info">
                        <strong>Mesa {mesa.numero}</strong>
                        <small>
                          {status === 'ocupada' && mesa.num_comensales
                            ? `${mesa.num_comensales} pers${elapsed ? ` · ${elapsed}` : ''}`
                            : `${mesa.capacidad ?? '?'} cap.`}
                        </small>
                      </span>
                      <span className="sidebar-table-row__right">
                        <b>{getStatusLabel(status)}</b>
                        {total > 0 ? <span className="sidebar-table-row__total">{formatCOP(total)}</span> : null}
                      </span>
                    </button>
                  )
                })}
            </div>
          </section>

          <div className="system-status">Sistema en linea</div>
        </aside>
      </main>

      {selectedMesa && (
        <div className="map-modal-overlay">
          <button className="map-modal-backdrop" type="button" aria-label="Cerrar" onClick={() => setSelectedMesa(null)} />
          <div ref={modalRef} className="map-modal-panel">
            <div className="map-modal-panel__header">
              <div>
                <h2>Abrir Mesa {selectedMesa.numero}</h2>
                <p>Capacidad: {selectedMesa.capacidad ?? '-'} personas</p>
              </div>
              <button type="button" className="map-modal-panel__close" onClick={() => setSelectedMesa(null)} aria-label="Cerrar">×</button>
            </div>

            <form onSubmit={handleSubmit} className="map-open-form">
              <label>
                <span>Numero de comensales</span>
                <input
                  type="number"
                  min={1}
                  max={capacidadSeleccionada}
                  value={numComensales}
                  onChange={(event) => {
                    const value = Number(event.target.value)
                    setNumComensales(Math.min(capacidadSeleccionada, Math.max(1, value || 1)))
                  }}
                />
              </label>

              <div className="map-open-form__quick">
                {Array.from({ length: capacidadSeleccionada }, (_, index) => index + 1).map((n) => (
                  <button key={n} type="button" className={numComensales === n ? 'is-selected' : ''} aria-pressed={numComensales === n} onClick={() => setNumComensales(n)}>
                    {n}
                  </button>
                ))}
              </div>

              <label>
                <span>Notas</span>
                <textarea value={notas} onChange={(event) => setNotas(event.target.value)} />
              </label>

              <div className="map-open-form__actions">
                <button type="button" onClick={() => setSelectedMesa(null)}>Cancelar</button>
                <button type="submit" disabled={abrirMesaMutation.isLoading || !numComensales || numComensales < 1 || numComensales > capacidadSeleccionada}>
                  {abrirMesaMutation.isLoading ? 'Abriendo...' : 'Abrir Mesa'}
                </button>
              </div>

              {abrirMesaMutation.isError ? (
                <p>{abrirMesaMutation.error?.response?.data?.detail || 'Error al abrir la mesa'}</p>
              ) : null}
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
