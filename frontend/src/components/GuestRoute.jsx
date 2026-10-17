import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { ROLE_HOME_PATH } from '../constants/roles';

export default function GuestRoute() {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div style={{ padding: '48px', textAlign: 'center', color: '#64748B' }}>
        Đang kiểm tra trạng thái đăng nhập...
      </div>
    );
  }

  if (isAuthenticated && user) {
    const userRole = user.role === 'ADMIN' ? 'ADMIN' : user.user_type || user.role;
    const targetPath = ROLE_HOME_PATH[userRole] || '/candidate';
    return <Navigate to={targetPath} replace />;
  }

  return <Outlet />;
}