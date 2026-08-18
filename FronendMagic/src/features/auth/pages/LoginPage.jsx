import { useState } from 'react'
import { useNavigate, Navigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [tenantSlug, setTenantSlug] = useState(
    localStorage.getItem('mvpos_tenant_slug') || ''
  )
  const [isPasswordVisible, setIsPasswordVisible] = useState(false)
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

    if (!tenantSlug.trim()) {
      setError('El identificador del restaurante es requerido')
      return
    }

    setLoading(true)

    try {
      await login(username, password, tenantSlug.trim().toLowerCase())
      navigate('/mesas')
    } catch (err) {
      if (!err?.response) {
        setError('No se pudo conectar con el servidor. Verifica que el backend esté encendido.')
      } else {
        const detail = err.response.data?.detail
        const apiMessage = err.response.data?.error?.message
        setError(detail || apiMessage || 'Credenciales inválidas')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page-shell">
      <div className="login-card">
        <div className="login-card__header">
          <div className="login-card__icon" aria-hidden="true">
            <svg viewBox="0 0 64 64">
              <path d="M20 11v19M16 11h8M16 17h8M20 30v23M44 11v42M40 11h8M40 19h8M32 14 13 50M32 14l19 36" />
            </svg>
          </div>
          <div className="login-card__title-group">
            <h1 className="login-card__title">Bienvenido</h1>
            <p className="login-card__subtitle">Accede al panel de administración del restaurante</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} aria-label="login-form" className="login-form">

          <label className="login-label">
            Restaurante
            <input
              value={tenantSlug}
              onChange={(e) => setTenantSlug(e.target.value)}
              className="login-input"
              placeholder="ej: mv"
              autoComplete="organization"
              required
            />
          </label>

          <label className="login-label">
            Usuario
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="login-input"
              placeholder="ej: carlos.mendez"
              autoComplete="username"
              required
            />
          </label>

          <label className="login-label">
            Contraseña
            <span className="login-password-field">
              <input
                type={isPasswordVisible ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="login-input"
                placeholder="Ingresa tu contraseña"
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                className="login-password-toggle"
                aria-label={isPasswordVisible ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                aria-pressed={isPasswordVisible}
                onClick={() => setIsPasswordVisible((visible) => !visible)}
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  {isPasswordVisible ? (
                    <><path d="M3 3l18 18" /><path d="M10.6 10.6a2 2 0 0 0 2.8 2.8" /><path d="M9.9 4.2A10.6 10.6 0 0 1 12 4c5.5 0 9.3 5 9.8 7.7a12.4 12.4 0 0 1-3.3 5.1M6.1 6.1C3.9 7.7 2.5 10.1 2.2 11.7 2.7 14.4 6.5 19.4 12 19.4c1 0 2-.2 2.8-.5" /></>
                  ) : (
                    <><path d="M2.2 12S5.7 4.6 12 4.6 21.8 12 21.8 12 18.3 19.4 12 19.4 2.2 12 2.2 12Z" /><circle cx="12" cy="12" r="3.1" /></>
                  )}
                </svg>
              </button>
            </span>
          </label>

          <a className="login-forgot-password" href="/recuperar-contrasena">¿Olvidaste tu contraseña?</a>

          <button type="submit" disabled={loading} className="login-button">
            {loading ? 'Cargando...' : 'Entrar'}
          </button>

          {error && <p className="login-error">{error}</p>}
        </form>

        <div className="login-footer">
          <p>Restaurante de alta gastronomía. Gestión segura y sofisticada.</p>
        </div>
      </div>
    </div>
  )
}
