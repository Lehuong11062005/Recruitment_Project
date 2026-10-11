import { Navigate, Outlet } from 'react-router-dom'
import { ROLE_HOME } from '../constants/roles'
import { useAuth } from '../hooks/useAuth'

// Trang chỉ dành cho người chưa đăng nhập (login, register). Đã đăng nhập thì chuyển về trang chủ theo vai trò.
export default function GuestRoute() {
  const { isAuthenticated, user } = useAuth()
  if (isAuthenticated) return <Navigate to={ROLE_HOME[user.role] ?? '/'} replace />
  return <Outlet />
}
