import { Link } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import Icon from '../../components/Icon';

export default function CandidateDashboard() {
  const { user } = useAuth();

  return (
    <div className="content-stack">
      <section className="card welcome-card">
        <div>
          <span className="badge badge-blue"><Icon name="spark" size={14} /> Không gian ứng viên</span>
          <h2 className="display-title">Xin chào, {user?.full_name || 'Ứng viên'}</h2>
          <p className="muted">Theo dõi cơ hội nghề nghiệp và trạng thái hồ sơ ứng tuyển của bạn.</p>
          <div className="button-row">
            <Link to="/candidate/jobs" className="btn btn-primary">Khám phá việc làm</Link>
            <Link to="/candidate/applications" className="btn btn-secondary">Xem đơn ứng tuyển</Link>
          </div>
        </div>
      </section>

      <section className="card">
        <div className="card-header">
          <div>
            <h3 className="section-title">Bắt đầu với CareerAI</h3>
            <p className="muted small">Các khu vực làm việc hiện có trong tài khoản của bạn.</p>
          </div>
        </div>
        <div className="dashboard-shortcuts">
          <Link to="/candidate/jobs" className="shortcut-card">
            <span className="stat-icon"><Icon name="search" /></span>
            <strong>Tìm việc làm</strong>
            <span className="muted small">Tìm kiếm và xem thông tin tuyển dụng.</span>
            <span className="inline-link">Xem cơ hội <Icon name="chevron" size={15} /></span>
          </Link>
          <Link to="/candidate/applications" className="shortcut-card">
            <span className="stat-icon stat-purple"><Icon name="briefcase" /></span>
            <strong>Đơn ứng tuyển</strong>
            <span className="muted small">Theo dõi các hồ sơ đã gửi.</span>
            <span className="inline-link">Theo dõi hồ sơ <Icon name="chevron" size={15} /></span>
          </Link>
          <Link to="/candidate/messages" className="shortcut-card">
            <span className="stat-icon stat-green"><Icon name="message" /></span>
            <strong>Tin nhắn</strong>
            <span className="muted small">Trao đổi với nhà tuyển dụng.</span>
            <span className="inline-link">Mở tin nhắn <Icon name="chevron" size={15} /></span>
          </Link>
        </div>
      </section>
    </div>
  );
}
