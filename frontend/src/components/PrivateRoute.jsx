import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

/**
 * Bảo vệ route theo đăng nhập và vai trò.
 *   <Route element={<PrivateRoute allowedRoles={[ROLES.CANDIDATE]} />}> ...routes con... </Route>
 * - Chưa đăng nhập        -> /login (nhớ trang đang vào để quay lại sau khi đăng nhập)
 * - Đăng nhập sai vai trò -> /403
 * Lưu ý: đây chỉ là chặn ở giao diện. Backend/Gateway vẫn phải kiểm tra quyền cho mọi API.
 */
export default function PrivateRoute({ allowedRoles }) {
  const { isAuthenticated, user } = useAuth()
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/403" replace />
  }
  return <Outlet />
}
