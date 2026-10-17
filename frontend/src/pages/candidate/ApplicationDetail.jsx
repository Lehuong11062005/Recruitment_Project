import { Link, useParams } from 'react-router-dom';
import Icon from '../../components/Icon';

export default function ApplicationDetail() {
  const { applicationId } = useParams();

  return (
    <div className="content-stack">
      <Link to="/candidate/applications" className="inline-link">
        <Icon name="chevron" size={16} className="back-chevron" /> Quay lại đơn ứng tuyển
      </Link>
      <section className="card application-detail-head">
        <div className="company-logo company-logo-large logo-blue"><Icon name="file" /></div>
        <div>
          <span className="badge badge-gray">Đơn ứng tuyển</span>
          <h2 className="display-title">Chi tiết hồ sơ</h2>
          <span className="muted small">Mã đơn: {applicationId}</span>
        </div>
      </section>
      <div className="detail-layout">
        <div className="content-stack">
          <section className="card">
            <div className="card-header">
              <div>
                <h3 className="section-title">Lịch sử trạng thái</h3>
                <p className="muted small">Các cập nhật trạng thái của hồ sơ ứng tuyển.</p>
              </div>
            </div>
            <div className="empty-state">
              <Icon name="clock" size={25} />
              <strong>Chưa có dữ liệu trạng thái</strong>
              <p>Lịch sử xử lý sẽ xuất hiện tại đây khi thông tin đơn ứng tuyển được tải từ hệ thống.</p>
            </div>
          </section>
          <section className="card">
            <div className="card-header">
              <div>
                <h3 className="section-title">Thông tin hồ sơ</h3>
                <p className="muted small">Thông tin vị trí và CV đã gửi.</p>
              </div>
            </div>
            <div className="empty-state">
              <Icon name="file" size={25} />
              <strong>Thông tin đơn chưa khả dụng</strong>
              <p>Không tìm thấy dữ liệu chi tiết cho mã đơn {applicationId} trong giao diện hiện tại.</p>
              <Link to="/candidate/messages" className="btn btn-secondary">
                <Icon name="message" size={16} /> Mở tin nhắn
              </Link>
            </div>
          </section>
        </div>
        <aside className="card analysis-detail">
          <div className="card-header">
            <div>
              <h3 className="section-title">Phân tích AI</h3>
              <p className="muted small">Kết quả phù hợp của hồ sơ ứng tuyển.</p>
            </div>
          </div>
          <div className="empty-state">
            <Icon name="spark" size={25} />
            <strong>Chưa có kết quả phân tích</strong>
            <p>Kết quả AI sẽ hiển thị khi được cung cấp bởi hệ thống.</p>
          </div>
        </aside>
      </div>
    </div>
  );
}
