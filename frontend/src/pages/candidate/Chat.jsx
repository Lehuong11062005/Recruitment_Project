import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import Icon from '../../components/Icon';

export default function Chat() {
  const { conversationId } = useParams();
  const [message, setMessage] = useState('');

  return (
    <section className="card message-shell full-chat chat-page">
      <div className="conversation">
        <div className="conversation-head">
          <span className="avatar avatar-blue"><Icon name="message" size={18} /></span>
          <div>
            <strong>{conversationId ? 'Cuộc hội thoại' : 'Tin nhắn'}</strong>
            <span>{conversationId ? `Mã hội thoại: ${conversationId}` : 'Trao đổi với nhà tuyển dụng'}</span>
          </div>
        </div>
        <div className="messages chat-placeholder">
          <Icon name="message" size={28} />
          {conversationId ? (
            <>
              <strong>Chưa có nội dung hội thoại</strong>
              <p>Tin nhắn của cuộc hội thoại này sẽ hiển thị khi dữ liệu được tải từ hệ thống.</p>
            </>
          ) : (
            <>
              <strong>Chưa chọn cuộc hội thoại</strong>
              <p>Cuộc hội thoại được mở từ thông tin ứng tuyển khi có dữ liệu tương ứng.</p>
              <Link to="/candidate/applications" className="inline-link">Xem đơn ứng tuyển</Link>
            </>
          )}
        </div>
        <form className="composer" onSubmit={(event) => { event.preventDefault(); setMessage(''); }}>
          <input
            aria-label="Nội dung tin nhắn"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Nhập nội dung tin nhắn..."
          />
          <button className="btn btn-primary" type="submit" disabled={!message.trim()}>
            <Icon name="send" size={16} /> Gửi
          </button>
        </form>
      </div>
    </section>
  );
}
