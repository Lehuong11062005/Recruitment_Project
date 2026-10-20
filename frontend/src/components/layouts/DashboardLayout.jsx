import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import Icon from '../Icon';

const PAGE_COPY = {
  '/candidate': ['Tổng quan ứng viên', 'Theo dõi hồ sơ và cơ hội việc làm phù hợp.'],
  '/candidate/profile': ['Hồ sơ ứng viên', 'Cập nhật thông tin, kỹ năng, kinh nghiệm và CV.'],
  '/candidate/jobs': ['Tìm kiếm việc làm', 'Khám phá các cơ hội đang tuyển dụng.'],
  '/candidate/applications': ['Đơn ứng tuyển của tôi', 'Theo dõi trạng thái hồ sơ đã nộp.'],
  '/candidate/messages': ['Tin nhắn trực tiếp', 'Trao đổi với nhà tuyển dụng.'],
  '/recruiter': ['Quản lý tin tuyển dụng', 'Theo dõi các vị trí tuyển dụng của doanh nghiệp.'],
  '/recruiter/jobs': ['Quản lý tin tuyển dụng', 'Theo dõi các vị trí tuyển dụng của doanh nghiệp.'],
  '/admin': ['Dashboard quản trị', 'Quản lý và giám sát nền tảng.'],
};

const ROLE_NAV = {
  candidate: [
    { to: '/candidate', label: 'Tổng quan', icon: 'grid', end: true },
    { to: '/candidate/profile', label: 'Hồ sơ cá nhân', icon: 'user' },
    { to: '/candidate/jobs', label: 'Tìm việc làm', icon: 'search' },
    { to: '/candidate/applications', label: 'Đơn ứng tuyển', icon: 'briefcase' },
    { to: '/candidate/messages', label: 'Tin nhắn', icon: 'message' },
  ],
  recruiter: [{ to: '/recruiter/jobs', label: 'Tin tuyển dụng', icon: 'briefcase' }],
  admin: [{ to: '/admin', label: 'Trung tâm quản trị', icon: 'shield', end: true }],
};

const ROLE_NAMES = {
  candidate: 'ỨNG VIÊN',
  recruiter: 'NHÀ TUYỂN DỤNG',
  admin: 'QUẢN TRỊ VIÊN',
};

const initials = (name = '') => name
  .split(/\s+/)
  .filter(Boolean)
  .slice(-2)
  .map((part) => part[0])
  .join('')
  .toUpperCase();

export default function DashboardLayout({ roleLabel, role = 'candidate' }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [title, subtitle] = PAGE_COPY[pathname] || (
    pathname.startsWith('/candidate/jobs/')
      ? ['Chi tiết việc làm', 'Thông tin tuyển dụng và ứng tuyển.']
      : pathname.startsWith('/candidate/applications/')
        ? ['Chi tiết đơn ứng tuyển', 'Theo dõi tiến trình xử lý hồ sơ.']
        : ['Tin nhắn trực tiếp', 'Trao đổi với nhà tuyển dụng.']
  );
  const navItems = ROLE_NAV[role];
  const displayName = user?.full_name || user?.email || roleLabel;
  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <NavLink to="/" className="brand">
          <span className="brand-mark"><Icon name="spark" size={20} /></span>
          <span>CareerAI</span>
        </NavLink>
        <div className="workspace-label">{ROLE_NAMES[role]}</div>
        <nav aria-label="Điều hướng chính">
          {navItems.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => (isActive ? 'active' : '')} title={item.label}>
              <Icon name={item.icon} size={19} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-account">
          <div className="sidebar-user">
            <span className="avatar avatar-blue">{initials(displayName) || 'U'}</span>
            <span className="sidebar-user-copy"><strong>{displayName}</strong><small>{user?.email || roleLabel}</small></span>
          </div>
          <button type="button" className="logout-button" onClick={handleLogout} title="Đăng xuất">
            <Icon name="logout" size={18} /><span>Đăng xuất</span>
          </button>
        </div>
      </aside>
      <main className="main-area">
        <header className="topbar">
          <div className="page-heading"><h1 className="page-title">{title}</h1><span>{subtitle}</span></div>
          <div className="top-actions">
            <span className="topbar-avatar avatar avatar-blue">{initials(displayName) || 'U'}</span>
            <span className="topbar-identity"><strong>{displayName}</strong><small>{roleLabel}</small></span>
          </div>
        </header>
        <div className="page-content"><Outlet /></div>
      </main>
    </div>
  );
}
