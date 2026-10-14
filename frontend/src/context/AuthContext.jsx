import { useCallback, useEffect, useMemo, useState } from 'react'
import { AuthContext } from './authState'
import { authService } from '../services/authService'
import { MOCK_AUTH } from '../config/env'
import { getUserRole } from '../constants/roles'
import { storage } from '../utils/storage'
import { isTokenExpired } from '../utils/jwt'

const EMPTY = { token: null, user: null }

// Khôi phục phiên đăng nhập khi tải lại trang
function loadInitial() {
  const token = storage.getToken()
  const user = storage.getUser()
  if (!token || !user || isTokenExpired(token)) {
    storage.clear()
    return EMPTY
  }
  return { token, user }
}

// Chuyển user từ API (snake_case) sang dạng dùng trong giao diện
function toAppUser(apiUser) {
  return {
    id: apiUser.id,
    fullName: apiUser.full_name,
    email: apiUser.email,
    phone: apiUser.phone,
    companyId: apiUser.company_id,
    role: getUserRole(apiUser), // CANDIDATE | RECRUITER | ADMIN
  }
}

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(loadInitial)

  const persist = useCallback((token, user) => {
    storage.setToken(token)
    storage.setUser(user)
    setAuth({ token, user })
  }, [])

  // Đăng nhập thật: POST /api/v1/auth/login -> { access_token, user }
  const login = useCallback(
    async (credentials) => {
      const data = await authService.login(credentials)
      const user = toAppUser(data.user)
      if (!data.access_token || !user.role) {
        throw new Error('Phản hồi đăng nhập thiếu access_token hoặc vai trò')
      }
      persist(data.access_token, user)
      return user
    },
    [persist],
  )

  // Đăng nhập giả để test phân quyền khi backend chưa sẵn sàng (VITE_MOCK_AUTH=true)
  const mockLogin = useCallback(
    (role) => {
      const user = { id: `mock-${role}`, fullName: `Demo ${role}`, email: `${role.toLowerCase()}@demo.local`, role }
      persist('mock-token', user)
      return user
    },
    [persist],
  )

  const logout = useCallback(() => {
    storage.clear()
    setAuth(EMPTY)
  }, [])

  // Axios gặp 401 thì phát sự kiện này
  useEffect(() => {
    const handler = () => setAuth(EMPTY)
    window.addEventListener('auth:logout', handler)
    return () => window.removeEventListener('auth:logout', handler)
  }, [])

  const value = useMemo(
    () => ({
      user: auth.user,
      token: auth.token,
      isAuthenticated: Boolean(auth.token && auth.user),
      isMockAuth: MOCK_AUTH,
      login,
      mockLogin,
      logout,
    }),
    [auth, login, mockLogin, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
