import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../features/auth/hooks/useAuth'

export default function PrivateRoute({ roles }) {
  const { isAuthenticated, initialized, user } = useAuth()

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

  if (roles && !roles.includes(user?.rol)) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
