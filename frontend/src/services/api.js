import axios from 'axios'
import { API_URL } from '../config/env'
import { storage } from '../utils/storage'

/**
 * Axios dùng chung, trỏ về API Gateway (http://localhost:8000).
 * Các service gọi dạng:  api.get('/api/v1/jobs')
 */
const api = axios.create({
  baseURL: API_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

// Gắn JWT vào mọi request
api.interceptors.request.use((config) => {
  const token = storage.getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`

  // Upload file (UC-C5): để trình duyệt tự đặt multipart boundary
  if (config.data instanceof FormData) delete config.headers['Content-Type']
  return config
})

// Trả thẳng body (res.data); gặp 401 thì xóa phiên và báo cho AuthProvider
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      storage.clear()
      window.dispatchEvent(new Event('auth:logout'))
    }
    return Promise.reject(error)
  },
)

export default api
