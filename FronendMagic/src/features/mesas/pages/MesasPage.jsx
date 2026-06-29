import { useState, useEffect, useRef, useMemo } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useMesas } from '../hooks/useMesas'
import { useAbrirMesa } from '../hooks/useAbrirMesa'
import { useAuth } from '../../auth/hooks/useAuth'

const tableLayouts = {
  1: { zone: 'principal', x: 22, y: 22, shape: 'round' },
  2: { zone: 'principal', x: 68, y: 22, shape: 'round' },
  3: { zone: 'principal', x: 22, y: 58, shape: 'round' },
  4: { zone: 'principal', x: 68, y: 58, shape: 'round' },
  5: { zone: 'principal', x: 50, y: 86, shape: 'wide' },
  6: { zone: 'terraza', x: 54, y: 28, shape: 'wide' },
  7: { zone: 'terraza', x: 50, y: 78, shape: 'round' },
  8: { zone: 'bar', x: 50, y: 52, shape: 'round' },
}

const zoneConfig = {
  principal: {
    label: 'Salon Principal',
    className: 'zone-principal',
    style: { left: '8%', top: '37%', width: '38%', height: '48%' },
  },
  terraza: {
    label: 'Terraza',
    className: 'zone-terraza',
    style: { left: '52%', top: '37%', width: '30%', height: '24%' },
  },
  bar: {
    label: 'Bar',
    className: 'zone-bar',
    style: { left: '52%', top: '66%', width: '30%', height: '22%' },
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

export default function MesasPage() {
  const [selectedMesa, setSelectedMesa] = useState(null)
  const [numComensales, setNumComensales] = useState(1)
  const [notas, setNotas] = useState('')
  const [time, setTime] = useState(new Date())
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

  const stats = useMemo(() => {
    const libres = mesas.filter((mesa) => normalizeStatus(mesa) === 'libre').length
    const ocupadas = mesas.filter((mesa) => normalizeStatus(mesa) === 'ocupada').length
    const reservadas = mesas.filter((mesa) => normalizeStatus(mesa) === 'reservada').length
    return { libres, ocupadas, reservadas, total: mesas.length }
  }, [mesas])

  const mesasByZone = useMemo(() => {
    return mesas.reduce((acc, mesa, index) => {
      const zone = getZoneKey(mesa)
      const layout = tableLayouts[Number(mesa.numero)] || {
        zone,
        x: 18 + ((index * 24) % 68),
        y: 22 + ((index * 18) % 58),
        shape: index % 3 === 0 ? 'wide' : 'round',
      }
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

        <div className="restaurant-header-stats">
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
          <button type="button" className="restaurant-header-button" onClick={() => navigate('/inventario')}>
            Inventario
          </button>
          <button type="button" className="restaurant-header-button restaurant-header-button--recipes" onClick={() => navigate('/recetario')}>
            Recetario
          </button>
          <button type="button" className="restaurant-header-button" onClick={() => navigate('/cierre-caja')}>
            Cierre de caja
          </button>
          {['cajero', 'administrador'].includes(user?.rol) ? (
            <button type="button" className="restaurant-header-button" onClick={() => navigate('/finanzas')}>
              Finanzas
            </button>
          ) : null}
          {['cajero', 'administrador'].includes(user?.rol) ? (
            <button type="button" className="restaurant-header-button restaurant-header-button--bold" onClick={() => navigate('/bold-prueba')}>
              Pago Bold prueba
            </button>
          ) : null}
          <button type="button" className="restaurant-header-button restaurant-header-button--danger" onClick={() => logout()}>
            Cerrar sesion
          </button>
        </div>
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
                <div key={zoneKey} className={`floor-zone ${zone.className}`} style={zone.style}>
                  <div className="floor-zone__label">{zone.label}</div>
                  {zoneKey === 'bar' ? <div className="floor-zone__bar-label">BARRA</div> : null}

                  {(mesasByZone[zoneKey] || []).map((mesa) => {
                    const status = normalizeStatus(mesa)
                    return (
                      <button
                        key={mesa.id}
                        type="button"
                        className={`floor-table floor-table--${mesa.layout.shape} floor-table--${status}`}
                        style={{ left: `${mesa.layout.x}%`, top: `${mesa.layout.y}%` }}
                        onClick={() => handleMesaAction(mesa)}
                      >
                        <span className="floor-table__dot" />
                        <strong>Mesa {mesa.numero}</strong>
                        <small>{mesa.capacidad ?? '?'} personas</small>
                        <span className="floor-table__tooltip">
                          <strong>Mesa {mesa.numero}</strong>
                          <small>{mesa.capacidad ?? '?'} personas - {zone.label}</small>
                          <b>{getStatusLabel(status)}</b>
                        </span>
                      </button>
                    )
                  })}
                </div>
              ))}

              <div className="floor-entrance">Entrada principal</div>
            </>
          ) : null}
        </section>

        <aside className="restaurant-sidebar">
          <section className="sidebar-block">
            <h2>Estado General</h2>
            <div className="occupancy-ring" style={{ '--busy': `${stats.total ? (stats.ocupadas / stats.total) * 360 : 0}deg` }}>
              <div>
                <strong>{stats.ocupadas}</strong>
                <span>ocupadas</span>
              </div>
            </div>
            <p>{stats.total} mesas en total</p>
          </section>

          <section className="sidebar-zones">
            {Object.entries(zoneConfig).map(([zoneKey, zone]) => (
              <div key={zoneKey} className={`sidebar-zone ${zone.className}`}>
                <span />
                <div>
                  <strong>{zone.label}</strong>
                  <small>{zoneStats[zoneKey]?.ocupadas || 0}/{zoneStats[zoneKey]?.total || 0} ocupadas</small>
                </div>
              </div>
            ))}
          </section>

          <section className="sidebar-table-list">
            <h2>Mesas</h2>
            <div className="sidebar-table-list__scroll">
              {mesas.map((mesa) => {
                const status = normalizeStatus(mesa)
                return (
                  <button key={mesa.id} type="button" className="sidebar-table-row" onClick={() => handleMesaAction(mesa)}>
                    <span className={`sidebar-table-row__dot sidebar-table-row__dot--${status}`} />
                    <span>
                      <strong>Mesa {mesa.numero}</strong>
                      <small>{mesa.capacidad ?? '?'} personas</small>
                    </span>
                    <b>{getStatusLabel(status)}</b>
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
              <button type="button" onClick={() => setSelectedMesa(null)} aria-label="Cerrar">x</button>
            </div>

            <form onSubmit={handleSubmit} className="map-open-form">
              <label>
                <span>Numero de comensales</span>
                <input
                  type="number"
                  min={1}
                  value={numComensales}
                  onChange={(event) => setNumComensales(Number(event.target.value))}
                />
              </label>

              <div className="map-open-form__quick">
                {[1, 2, 3, 4, 5, 6].map((n) => (
                  <button key={n} type="button" onClick={() => setNumComensales(n)}>
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
                <button type="submit" disabled={abrirMesaMutation.isLoading || !numComensales || numComensales < 1}>
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
