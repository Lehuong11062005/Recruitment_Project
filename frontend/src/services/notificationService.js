import api from './api';

export const notificationService = {
  getNotifications: (params = {}) => api.get('/api/v1/notifications', { params }),
  markAsRead: (notificationId) =>
    api.patch(`/api/v1/notifications/${encodeURIComponent(String(notificationId))}/read`),
};
