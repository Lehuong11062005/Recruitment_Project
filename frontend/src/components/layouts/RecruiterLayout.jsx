import DashboardLayout from './DashboardLayout';

const RECRUITER_NAV = [
  { to: '/recruiter', label: 'Quản lý tin tuyển dụng (JD)', end: true },
];

export default function RecruiterLayout() {
  return <DashboardLayout roleLabel="Cổng Nhà tuyển dụng (HR)" navItems={RECRUITER_NAV} />;
}