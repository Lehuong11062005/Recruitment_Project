import api from './api';

export const chatService = {
  getConversations: () => api.get('/api/v1/conversations'),
  getMessages: (conversationId, params = {}) =>
    api.get(`/api/v1/conversations/${conversationId}/messages`, { params }),

  //HR tạo/lấy hội thoại với ứng viên. payload: { job_id, candidate_id }
  createConversation: (payload) => api.post('/api/v1/conversations', payload),
};