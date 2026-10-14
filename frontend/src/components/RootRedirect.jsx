import { Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { ROLE_HOME_PATH } from '../constants/roles';

export default function RootRedirect() {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return null;
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }

  const userRole = user.role === 'ADMIN' ? 'ADMIN' : user.user_type || user.role;
  return <Navigate to={ROLE_HOME_PATH[userRole] || '/candidate'} replace />;
}