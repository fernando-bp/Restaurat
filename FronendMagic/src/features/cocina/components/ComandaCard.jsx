import { useState } from 'react'
import { marcarItemListo } from '../services/cocinaService'

function tiempoTranscurrido(isoString) {
  if (!isoString) return '—'
  const diff = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000)
  if (diff < 60) return `${diff}s`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ${diff % 60}s`
  return `${Math.floor(diff / 3600)}h ${Math.floor((diff % 3600) / 60)}m`
}

function urgencyColor(isoString) {
  if (!isoString) return '#4ade80'
  const mins = (Date.now() - new Date(isoString).getTime()) / 60000
  if (mins > 20) return '#ef4444'
  if (mins > 10) return '#f59e0b'
  return '#4ade80'
}

export default function ComandaCard({ comanda, onItemListo }) {
  const [markingId, setMarkingId] = useState(null)

  async function handleListo(itemId) {
    setMarkingId(itemId)
    try {
      await marcarItemListo(itemId)
      onItemListo(itemId)
    } catch {
      // silently ignore — next poll will refresh state
    } finally {
      setMarkingId(null)
    }
  }

  const elapsed = tiempoTranscurrido(comanda.hora_confirmacion)
  const color = urgencyColor(comanda.hora_confirmacion)

  return (
    <div style={{
      background: '#1e293b',
      border: `2px solid ${color}`,
      borderRadius: 12,
      padding: '20px 24px',
      display: 'flex',
      flexDirection: 'column',
      gap: 12,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
          <span style={{ color: '#f8fafc', fontSize: 13, fontWeight: 600, letterSpacing: 1, textTransform: 'uppercase' }}>Mesa</span>
          <span style={{ color: color, fontSize: 40, fontWeight: 900, lineHeight: 1 }}>{comanda.mesa_numero}</span>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ color: color, fontSize: 22, fontWeight: 700, fontVariantNumeric: 'tabular-nums' }}>{elapsed}</div>
          <div style={{ color: '#94a3b8', fontSize: 12 }}>{comanda.num_comensales} comensales</div>
        </div>
      </div>

      {comanda.notas_generales && (
        <div style={{
          background: '#0f172a',
          borderLeft: '3px solid #f59e0b',
          padding: '6px 10px',
          borderRadius: 4,
          color: '#fbbf24',
          fontSize: 13,
        }}>
          {comanda.notas_generales}
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {comanda.items.map((item) => (
          <div key={item.item_id} style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            background: '#0f172a',
            borderRadius: 8,
            padding: '10px 14px',
          }}>
            <span style={{
              background: '#1d4ed8',
              color: '#fff',
              borderRadius: 6,
              minWidth: 32,
              height: 32,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 800,
              fontSize: 16,
              flexShrink: 0,
            }}>
              {item.cantidad}
            </span>
            <div style={{ flex: 1 }}>
              <div style={{ color: '#f1f5f9', fontSize: 15, fontWeight: 600 }}>{item.receta_nombre}</div>
              {item.notas && (
                <div style={{ color: '#94a3b8', fontSize: 12, marginTop: 2 }}>{item.notas}</div>
              )}
            </div>
            <button
              onClick={() => handleListo(item.item_id)}
              disabled={markingId === item.item_id}
              style={{
                background: markingId === item.item_id ? '#166534' : '#16a34a',
                color: '#fff',
                border: 'none',
                borderRadius: 8,
                padding: '8px 18px',
                fontWeight: 700,
                fontSize: 14,
                cursor: markingId === item.item_id ? 'not-allowed' : 'pointer',
                flexShrink: 0,
                transition: 'background 0.15s',
              }}
            >
              {markingId === item.item_id ? '...' : '✓ LISTO'}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
