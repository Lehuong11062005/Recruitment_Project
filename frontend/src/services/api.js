import axios from 'axios';
import { API_URL } from '../config/env';
import { storage } from '../utils/storage';

/**
 * Axios dùng chung, trỏ về API Gateway (http://localhost:8000).
 * Các service gọi dạng: api.get('/api/v1/jobs')
 */
const api = axios.create({
  baseURL: API_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Gắn JWT Bearer Token vào mọi request
api.interceptors.request.use((config) => {
  const token = storage.getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  // Upload file PDF (UC-C3, UC-C5): để trình duyệt tự đặt multipart boundary
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type'];
  }
  return config;
});

// Trả thẳng body (response.data); chuẩn hóa thông báo lỗi FastAPI (detail)
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status;
    const detail = error.response?.data?.detail;

    if (status === 401 && !error.config?.url?.includes('/auth/login')) {
      storage.clear();
      window.dispatchEvent(new Event('auth:logout'));
    }

    let message = 'Đã xảy ra lỗi kết nối máy chủ.';
    if (typeof detail === 'string') {
      message = detail;
    } else if (Array.isArray(detail) && detail.length > 0) {
      message = detail.map((d) => d.msg).join(', ');
    } else if (error.message) {
      message = error.message;
    }

    const customError = new Error(message);
    customError.status = status;
    customError.data = error.response?.data;
    return Promise.reject(customError);
  }
);

export default api;