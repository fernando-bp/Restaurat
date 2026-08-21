import { useState, useEffect, useCallback, useRef } from 'react'
import { getComandasCocina } from '../services/cocinaService'
import ComandaCard from '../components/ComandaCard'

const REFRESH_INTERVAL = 20

export default function CocinaPage() {
  const [comandas, setComanadas] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [countdown, setCountdown] = useState(REFRESH_INTERVAL)
  const countdownRef = useRef(REFRESH_INTERVAL)

  const fetchComanadas = useCallback(async () => {
    try {
      const data = await getComandasCocina()
      setComanadas(data.comandas || [])
      setLastUpdated(new Date())
      setError(null)
    } catch (err) {
      setError('Error al obtener comandas. Reintentando...')
    } finally {
      setLoading(false)
      countdownRef.current = REFRESH_INTERVAL
      setCountdown(REFRESH_INTERVAL)
    }
  }, [])

  useEffect(() => {
    fetchComanadas()
    const pollInterval = setInterval(fetchComanadas, REFRESH_INTERVAL * 1000)
    const tickInterval = setInterval(() => {
      countdownRef.current = Math.max(0, countdownRef.current - 1)
      setCountdown(countdownRef.current)
    }, 1000)
    return () => {
      clearInterval(pollInterval)
      clearInterval(tickInterval)
    }
  }, [fetchComanadas])

  function handleItemListo(itemId) {
    setComanadas((prev) =>
      prev
        .map((c) => ({
          ...c,
          items: c.items.filter((i) => i.item_id !== itemId),
        }))
        .filter((c) => c.items.length > 0),
    )
  }

  const now = new Date()
  const horaStr = now.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })

  return (
    <div style={{
      minHeight: '100vh',
      background: '#0f172a',
      color: '#f1f5f9',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Header */}
      <div style={{
        background: '#1e293b',
        borderBottom: '2px solid #334155',
        padding: '14px 28px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 24 }}>🍳</span>
          <span style={{ fontSize: 20, fontWeight: 800, letterSpacing: 1 }}>COCINA</span>
          {comandas.length > 0 && (
            <span style={{
              background: '#dc2626',
              color: '#fff',
              borderRadius: 20,
              padding: '2px 10px',
              fontSize: 14,
              fontWeight: 700,
            }}>
              {comandas.length} {comandas.length === 1 ? 'comanda' : 'comandas'}
            </span>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
          <span style={{ color: '#94a3b8', fontSize: 13 }}>
            {lastUpdated ? `Actualizado ${lastUpdated.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}` : ''}
          </span>
          <button
            onClick={fetchComanadas}
            style={{
              background: '#334155',
              color: '#94a3b8',
              border: 'none',
              borderRadius: 8,
              padding: '6px 14px',
              cursor: 'pointer',
              fontSize: 13,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            ↻ {countdown}s
          </button>
          <span style={{ color: '#64748b', fontSize: 20, fontWeight: 700, fontVariantNumeric: 'tabular-nums' }}>
            {horaStr}
          </span>
        </div>
      </div>

      {/* Body */}
      <div style={{ flex: 1, padding: 24 }}>
        {loading && (
          <div style={{ textAlign: 'center', color: '#64748b', fontSize: 18, marginTop: 80 }}>
            Cargando comandas...
          </div>
        )}

        {error && !loading && (
          <div style={{
            background: '#450a0a',
            border: '1px solid #dc2626',
            borderRadius: 10,
            padding: '14px 20px',
            color: '#fca5a5',
            marginBottom: 24,
          }}>
            {error}
          </div>
        )}

        {!loading && comandas.length === 0 && (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            marginTop: 100,
            gap: 16,
          }}>
            <span style={{ fontSize: 64 }}>✅</span>
            <div style={{ fontSize: 24, fontWeight: 700, color: '#4ade80' }}>¡Todo listo!</div>
            <div style={{ color: '#64748b', fontSize: 16 }}>No hay comandas pendientes en cocina.</div>
          </div>
        )}

        {!loading && comandas.length > 0 && (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
            gap: 20,
          }}>
            {comandas.map((comanda) => (
              <ComandaCard
                key={comanda.orden_id}
                comanda={comanda}
                onItemListo={handleItemListo}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
