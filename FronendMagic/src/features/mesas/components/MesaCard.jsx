import libreImg from '../libre.png'
import ocupadaImg from '../ocupada.png'
import reservaImg from '../reserva.png'

const statusMap = {
  libre: { label: 'Libre', color: '#10B981', image: libreImg },
  ocupada: { label: 'Ocupada', color: '#EF4444', image: ocupadaImg },
  reservada: { label: 'Reserva', color: '#F59E0B', image: reservaImg },
  en_preparacion: { label: 'Preparación', color: '#F97316', image: reservaImg },
  default: { label: 'Desconocido', color: '#9CA3AF', image: libreImg },
}

function getStatus(estado) {
  if (!estado) return statusMap.default
  const key = estado.toLowerCase().replace(/\s+/g, '_')
  return statusMap[key] || statusMap.default
}

export default function MesaCard({ mesa, onClick }) {
  const status = getStatus(mesa.estado)

  return (
    <div
      role="button"
      className="mesa-card"
      data-state={(status.label || '').toLowerCase()}
      onClick={() => onClick?.(mesa)}
      onKeyDown={(e) => e.key === 'Enter' && onClick?.(mesa)}
      tabIndex={0}
      style={{
        border: `3px solid ${status.color}`,
      }}
      onMouseDown={(e) => (e.currentTarget.style.transform = 'scale(0.995)')}
      onMouseUp={(e) => (e.currentTarget.style.transform = 'scale(1)')}
      onMouseLeave={(e) => (e.currentTarget.style.transform = 'scale(1)')}
    >
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
        <div style={{ width: 84, height: 84, borderRadius: 12, background: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 6px 18px rgba(2,6,23,0.06)' }}>
          <img src={status.image} alt={status.label} style={{ width: 64, height: 64, objectFit: 'contain' }} />
        </div>

        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 20, fontWeight: 800, color: '#0f172a' }}>Mesa {mesa.numero}</div>
          <div style={{ fontSize: 13, color: '#6b7280', marginTop: 6 }}>{mesa.capacidad ?? '?'} personas</div>
        </div>
      </div>

      <div style={{ width: '100%', marginTop: 8, padding: '10px 12px', borderRadius: 12, background: '#ffffff', textAlign: 'center' }}>
        <div style={{ color: status.color, fontWeight: 800 }}>{status.label}</div>
      </div>
    </div>
  )
}
