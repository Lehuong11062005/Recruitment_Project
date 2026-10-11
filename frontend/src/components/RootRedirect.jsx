import { Navigate } from 'react-router-dom'
import { ROLE_HOME } from '../constants/roles'
import { useAuth } from '../hooks/useAuth'

export default function RootRedirect() {
  const { isAuthenticated, user } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <Navigate to={ROLE_HOME[user.role] ?? '/login'} replace />
}
