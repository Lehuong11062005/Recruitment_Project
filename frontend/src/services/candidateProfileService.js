import api from './api';

// Các route này đã có trong services/core-service/app/routers/users.py và skills.py trên main.
export const candidateProfileService = {
  getProfile: () => api.get('/api/v1/users/me/profile'),
  updateProfile: (payload) => api.put('/api/v1/users/me/profile', payload),
  getSkills: () => api.get('/api/v1/skills', { params: { limit: 200 } }),
  uploadCV(file) {
    const formData = new FormData();
    formData.append('file', file); // field UploadFile đã xác nhận trong users.py
    return api.post('/api/v1/users/me/cv', formData);
  },
};
