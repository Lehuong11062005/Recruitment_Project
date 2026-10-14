import { useState } from 'react';
import { useParams } from 'react-router-dom';

export default function Chat() {
  const { conversationId } = useParams();
  const [message, setMessage] = useState('');

  return (
    <div>
      <h1 style={{ fontSize: '22px', fontWeight: 700, color: '#142B4A', marginBottom: '16px' }}>
        Tin nhắn trực tiếp với Nhà tuyển dụng (UC-C8)
      </h1>
      <div
        style={{
          backgroundColor: '#FFFFFF',
          border: '1px solid #DCE5F0',
          borderRadius: '12px',
          padding: '24px',
        }}
      >
        <p style={{ fontSize: '14px', color: '#64748B', marginBottom: '16px' }}>
          {conversationId
            ? `Đang mở cuộc hội thoại #${conversationId}`
            : 'Chọn một cuộc hội thoại từ đơn ứng tuyển để trao đổi qua WebSocket.'}
        </p>
        <div style={{ display: 'flex', gap: '10px' }}>
          <input
            type="text"
            className="form-input"
            placeholder="Nhập nội dung tin nhắn..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
          />
          <button
            type="button"
            className="btn-primary"
            style={{ width: '140px', height: '42px' }}
            onClick={() => setMessage('')}
          >
            Gửi tin
          </button>
        </div>
      </div>
    </div>
  );
}