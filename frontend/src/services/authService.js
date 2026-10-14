import api from './api';

export const authService = {
  /**
   * Đăng nhập tài khoản (UC-C1, UC-R1)
   * @param {Object} credentials - { email, password }
   * @returns {Promise<{ access_token: string, token_type: string, user: Object }>}
   */
  login: (credentials) => {
    return api.post('/api/v1/auth/login', {
      email: credentials.email.trim().toLowerCase(),
      password: credentials.password,
    });
  },

  /**
   * Đăng ký tài khoản mới (UC-C1, UC-R1)
   * @param {Object} payload - { email, password, full_name, phone, user_type }
   * @returns {Promise<Object>} UserResponse (201 Created)
   */
  register: (payload) => {
    const body = {
      email: payload.email.trim().toLowerCase(),
      password: payload.password,
      full_name: payload.full_name.trim(),
      phone: payload.phone && payload.phone.trim() ? payload.phone.trim() : null,
      user_type: payload.user_type,
    };
    return api.post('/api/v1/auth/register', body);
  },

  /**
   * Lấy thông tin tài khoản hiện tại từ JWT token
   * @returns {Promise<Object>} UserResponse
   */
  getMe: () => {
    return api.get('/api/v1/auth/me');
  },
};