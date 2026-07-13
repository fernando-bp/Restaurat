import { useState } from 'react'
import { useNavigate, Navigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const { login, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  if (isAuthenticated) {
    return <Navigate to="/mesas" replace />
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError(null)
    setLoading(true)

    try {
      await login(username, password)
      navigate('/mesas')
    } catch (err) {
      if (!err?.response) {
        setError('No se pudo conectar con el servidor. Verifica que el backend este encendido.')
      } else {
        const detail = err.response.data?.detail
        const apiMessage = err.response.data?.error?.message
        setError(detail || apiMessage || 'Credenciales invalidas')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(180deg,#0b1220 0%, #0f1724 100%)', padding: 24 }}>
      <div style={{ width: 420, borderRadius: 16, padding: 28, background: 'linear-gradient(180deg, rgba(255,255,255,0.98), #ffffff)', boxShadow: '0 20px 50px rgba(2,6,23,0.4)' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12, marginBottom: 8 }}>
          <div style={{ width: 64, height: 64, borderRadius: 14, background: '#10B981', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 800, fontSize: 28 }}>🍽</div>
          <h1 style={{ margin: 0, fontSize: 22, color: '#0f1724' }}>Bienvenido</h1>
          <div style={{ color: '#6b7280', fontSize: 13 }}>Ingresa tus credenciales para continuar</div>
        </div>

        <form onSubmit={handleSubmit} aria-label="login-form">
          <div style={{ display: 'grid', gap: 12 }}>
            <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <span style={{ fontSize: 13, color: '#374151', fontWeight: 700 }}>Usuario</span>
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                style={{ width: '100%', padding: '14px 16px', marginTop: 0, borderRadius: 10, border: '1px solid #e6edf3', fontSize: 16 }}
                placeholder="ej: carlos.mendez"
                autoComplete="username"
                required
              />
            </label>

            <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <span style={{ fontSize: 13, color: '#374151', fontWeight: 700 }}>Contraseña</span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{ width: '100%', padding: '14px 16px', marginTop: 0, borderRadius: 10, border: '1px solid #e6edf3', fontSize: 16 }}
                placeholder="Ingresa tu contraseña"
                autoComplete="current-password"
                required
              />
            </label>

            <button
              type="submit"
              disabled={loading}
              style={{ width: '100%', padding: 14, background: '#10B981', color: '#fff', border: 'none', borderRadius: 10, fontWeight: 800, fontSize: 16, cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.85 : 1 }}
            >
              {loading ? 'Cargando...' : 'Entrar'}
            </button>

            {error && <p style={{ marginTop: 6, color: '#b91c1c', textAlign: 'center' }}>{error}</p>}
          </div>
        </form>
      </div>
    </div>
  )
}
