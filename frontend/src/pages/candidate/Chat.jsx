import { Link, useParams } from 'react-router-dom';
import Icon from '../../components/Icon';

export default function Chat() {
  const { conversationId } = useParams();

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
          <span className="badge badge-amber">CHƯA XÁC MINH API</span>
          {conversationId ? (
            <>
              <strong>Chưa thể tải hội thoại</strong>
              <p>Core Service hiện chưa xác nhận API hội thoại và tin nhắn. Không có dữ liệu hội thoại nào được hiển thị.</p>
            </>
          ) : (
            <>
              <strong>Tính năng nhắn tin chưa khả dụng</strong>
              <p>API hội thoại chưa được xác minh. Gửi tin nhắn sẽ không được bật cho tới khi backend hỗ trợ.</p>
              <Link to="/candidate/applications" className="inline-link">Xem đơn ứng tuyển</Link>
            </>
          )}
        </div>
        <div className="composer">
          <input
            aria-label="Nội dung tin nhắn"
            disabled
            placeholder="Nhắn tin chưa khả dụng"
          />
          <button className="btn btn-primary" type="button" disabled>
            <Icon name="send" size={16} /> Gửi
          </button>
        </div>
      </div>
    </section>
  );
}
