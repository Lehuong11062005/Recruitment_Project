import { useAuth } from '../../hooks/useAuth';
import Icon from '../../components/Icon';

export default function ManageJobs() {
  const { user } = useAuth();

  return (
    <div className="content-stack">
      {!user?.company_id && (
        <div className="inline-alert alert-amber">
          <Icon name="warning" />
          <span>
            <strong>Chưa liên kết hồ sơ doanh nghiệp</strong>
            Tài khoản của bạn chưa có company_id. Vui lòng hoàn thiện hồ sơ doanh nghiệp trước khi đăng tin.
          </span>
        </div>
      )}
      <section className="card">
        <div className="card-header">
          <div>
            <h2 className="section-title">Danh sách tin tuyển dụng</h2>
            <p className="muted small">Theo dõi vị trí tuyển dụng và hồ sơ ứng viên.</p>
          </div>
        </div>
        <div className="empty-state">
          <Icon name="briefcase" size={27} />
          <strong>Chưa có dữ liệu tin tuyển dụng</strong>
          <p>Danh sách tin và chức năng quản lý sẽ hiển thị khi được kết nối với dịch vụ tuyển dụng.</p>
        </div>
      </section>
      <section className="card compact-card">
        <div className="card-header">
          <div>
            <h3 className="section-title">Ứng viên và AI Matching</h3>
            <p className="muted small">Danh sách ứng viên và điểm phù hợp theo từng vị trí.</p>
          </div>
        </div>
        <div className="empty-state">
          <Icon name="users" size={24} />
          <strong>Chưa có hồ sơ ứng viên</strong>
          <p>Hồ sơ ứng viên sẽ được hiển thị sau khi có tin tuyển dụng và lượt ứng tuyển.</p>
        </div>
      </section>
    </div>
  );
}
