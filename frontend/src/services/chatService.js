import api from './api'

// UC-C8: phần REST (danh sách hội thoại, lịch sử). Tin nhắn realtime đi qua WebSocket.
// Model backend: conversations { job_id, candidate_id, recruiter_id, last_message }, messages { conversation_id, sender_role, content, is_read }.
// LƯU Ý: chưa có router chat trong core-service nên đường dẫn là GIẢ ĐỊNH.
export const chatService = {
  getConversations: () => api.get('/api/v1/chat/conversations'),
  // Server tự xác định recruiter từ job, client chỉ gửi job_id
  openConversation: (jobId) => api.post('/api/v1/chat/conversations', { job_id: jobId }),
  // params: { before } (created_at của tin cũ nhất đang hiển thị), { limit }
  getMessages: (conversationId, params) =>
    api.get(`/api/v1/chat/conversations/${conversationId}/messages`, { params }),
}
