import api from './api'

// Endpoint THẬT của core-service (UC-C1)
export const authService = {
  // body: { email, password } -> { access_token, token_type, user: { id, email, full_name, phone, role, user_type, company_id, status } }
  login: (payload) => api.post('/api/v1/auth/login', payload),
  // body: { email, password (>= 8 ký tự), full_name, phone?, user_type: 'CANDIDATE' | 'RECRUITER' }
  register: (payload) => api.post('/api/v1/auth/register', payload),
  me: () => api.get('/api/v1/auth/me'),
}
