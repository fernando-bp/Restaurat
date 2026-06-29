import libreImg from '../libre.png'
import ocupadaImg from '../ocupada.png'
import reservaImg from '../reserva.png'

const statusConfig = {
  libre: {
    label: 'Libre',
    image: libreImg,
  },
  ocupada: {
    label: 'Ocupada',
    image: ocupadaImg,
  },
  reservada: {
    label: 'Reserva',
    image: reservaImg,
  },
  en_preparacion: {
    label: 'Preparación',
    image: reservaImg,
  },
  default: {
    label: 'Ocupada',
    image: ocupadaImg,
  },
}

export default function MesaStatusButton({ estado, onClick }) {
  const config = statusConfig[estado?.toLowerCase()?.replace(/\s+/g, '_')] || statusConfig.default

  return (
    <button
      type="button"
      aria-label={config.label}
      onClick={onClick}
      style={{
        width: '100%',
        height: '160px',
        padding: 0,
        border: 'none',
        borderRadius: 16,
        background: '#f3f4f6',
        cursor: 'pointer',
        transition: 'all 0.3s ease',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
        overflow: 'hidden',
        boxShadow: '0 8px 20px rgba(0, 0, 0, 0.15)',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'translateY(-4px)'
        e.currentTarget.style.boxShadow = '0 12px 30px rgba(0, 0, 0, 0.25)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateY(0)'
        e.currentTarget.style.boxShadow = '0 8px 20px rgba(0, 0, 0, 0.15)'
      }}
    >
      <img
        src={config.image}
        alt={config.label}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          display: 'block',
        }}
      />
    </button>
  )
}
