import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../features/auth/hooks/useAuth'

export default function PrivateRoute({ roles }) {
  const { isAuthenticated, initialized, user, logout } = useAuth()
  const userRole = typeof user?.rol === 'string' ? user.rol.trim().toLowerCase() : ''

  if (!initialized) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        Cargando...
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (roles && !roles.includes(userRole)) {
    return (
      <main style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: '1.5rem' }}>
        <section style={{ maxWidth: '28rem', textAlign: 'center' }}>
          <h1>Acceso no autorizado</h1>
          <p>Tu usuario no tiene un rol habilitado para esta seccion.</p>
          <button type="button" onClick={() => logout()}>Cerrar sesion</button>
        </section>
      </main>
    )
  }

  return <Outlet />
}
