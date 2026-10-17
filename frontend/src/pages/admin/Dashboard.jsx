import Icon from '../../components/Icon';

const MODULES = [
  { icon: 'users', title: 'Quản lý tài khoản', description: 'Tài khoản ứng viên, nhà tuyển dụng và trạng thái hoạt động.' },
  { icon: 'building', title: 'Doanh nghiệp', description: 'Hồ sơ doanh nghiệp và trạng thái kiểm duyệt.' },
  { icon: 'briefcase', title: 'Tin tuyển dụng', description: 'Tin đăng, trạng thái hiển thị và nội dung cần kiểm tra.' },
  { icon: 'grid', title: 'Thống kê hệ thống', description: 'Tổng quan hoạt động và tình trạng dịch vụ.' },
];

export default function Dashboard() {
  return (
    <div className="content-stack">
      <section className="card">
        <div className="card-header">
          <div>
            <h2 className="section-title">Trung tâm quản trị</h2>
            <p className="muted small">Các khu vực quản lý hiện có trong nền tảng.</p>
          </div>
        </div>
        <div className="admin-module-grid">
          {MODULES.map((module) => (
            <article className="admin-module-card" key={module.title}>
              <span className="stat-icon"><Icon name={module.icon} /></span>
              <div>
                <h3>{module.title}</h3>
                <p>{module.description}</p>
                <span className="muted small">Chưa có dữ liệu quản trị được kết nối.</span>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
