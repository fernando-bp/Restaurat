import { useAuth } from '../../features/auth/hooks/useAuth'

export default function RoleGuard({ roles, children }) {
  const { isAuthenticated, user } = useAuth()
  if (!isAuthenticated || !roles.includes(user?.rol)) {
    return null
  }
  return children
}
