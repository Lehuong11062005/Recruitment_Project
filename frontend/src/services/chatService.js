import api from './api';

export const chatService = {
  getConversations: () => api.get('/api/v1/conversations'),
  getMessages: (conversationId, params = {}) =>
    api.get(`/api/v1/conversations/${conversationId}/messages`, { params }),
};