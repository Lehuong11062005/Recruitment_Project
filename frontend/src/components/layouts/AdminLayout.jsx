import DashboardLayout from './DashboardLayout';

const ADMIN_NAV = [
  { to: '/admin', label: 'Bảng điều khiển Quản trị', end: true },
];

export default function AdminLayout() {
  return <DashboardLayout roleLabel="Hệ thống Quản trị viên (Admin)" navItems={ADMIN_NAV} />;
}