import { useState, useEffect } from 'react';
import { storage } from '../utils/storage';
import { decodeToken, isTokenExpired } from '../utils/jwt';
import { authService } from '../services/authService';
import { AuthContext } from './authState';

const normalizeUser = (rawUser, tokenPayload) => {
  if (!rawUser && !tokenPayload) return null;

  // Chuẩn hóa role nghiệp vụ cho Router (ADMIN, CANDIDATE, RECRUITER)
  const resolvedRole =
    rawUser?.role === 'ADMIN'
      ? 'ADMIN'
      : rawUser?.user_type || tokenPayload?.role || rawUser?.role;

  return {
    id: rawUser?.id || tokenPayload?.sub,
    email: rawUser?.email || tokenPayload?.email,
    full_name: rawUser?.full_name || '',
    phone: rawUser?.phone || null,
    role: resolvedRole,
    user_type: rawUser?.user_type || resolvedRole,
    company_id: rawUser?.company_id ?? null,
    status: rawUser?.status || 'ACTIVE',
  };
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      const token = storage.getToken();

      if (!token || isTokenExpired(token)) {
        storage.clear();
        setIsLoading(false);
        return;
      }

      const payload = decodeToken(token);
      const cachedUser = storage.getUser();

      if (cachedUser) {
        setUser(normalizeUser(cachedUser, payload));
        setIsAuthenticated(true);
      } else if (payload) {
        setUser(normalizeUser(null, payload));
        setIsAuthenticated(true);
      }

      // Đồng bộ lại thông tin mới nhất từ /api/v1/auth/me (nếu backend đang chạy)
      try {
        const freshUser = await authService.getMe();
        const normalized = normalizeUser(freshUser, payload);
        storage.setUser(normalized);
        setUser(normalized);
        setIsAuthenticated(true);
      } catch (err) {
        // Nếu lỗi 401/403 thì xóa phiên đăng nhập
        if (err?.status === 401 || err?.status === 403) {
          storage.clear();
          setUser(null);
          setIsAuthenticated(false);
        }
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []);

  const login = async (credentials) => {
    const data = await authService.login(credentials);
    const token = data.access_token;

    if (!token) {
      throw new Error('Không nhận được token từ hệ thống');
    }

    const payload = decodeToken(token);
    const normalizedUser = normalizeUser(data.user, payload);

    storage.setToken(token);
    storage.setUser(normalizedUser);

    setUser(normalizedUser);
    setIsAuthenticated(true);
    return normalizedUser;
  };

  const register = async (payload) => {
    return await authService.register(payload);
  };

  const logout = () => {
    storage.clear();
    setUser(null);
    setIsAuthenticated(false);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated,
        isLoading,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};