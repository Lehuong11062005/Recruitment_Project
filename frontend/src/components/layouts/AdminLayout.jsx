import { NavLink } from 'react-router-dom';
import Icon from '../Icon';
import DashboardLayout from './DashboardLayout';

const ADMIN_TABS = [
  { to: '/admin', label: 'Tổng quan thống kê', icon: 'grid', end: true },
  { to: '/admin/users', label: 'Quản lý người dùng', icon: 'users' },
  { to: '/admin/companies', label: 'Duyệt doanh nghiệp', icon: 'building' },
  { to: '/admin/jobs', label: 'Kiểm duyệt tin tuyển dụng', icon: 'briefcase' },
];

export default function AdminLayout() {
  return <DashboardLayout role="admin" roleLabel="Quản trị viên" extraHeader={(
    <nav className="admin-tab-bar" aria-label="Phân hệ quản trị">
      {ADMIN_TABS.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          end={tab.end}
          className={({ isActive }) => `admin-tab-link ${isActive ? 'active' : ''}`}
        >
          <Icon name={tab.icon} size={16} />
          <span>{tab.label}</span>
        </NavLink>
      ))}
    </nav>
  )} />;
}
