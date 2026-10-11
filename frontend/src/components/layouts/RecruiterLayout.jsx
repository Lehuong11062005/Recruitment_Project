import DashboardLayout from './DashboardLayout'

const NAV_ITEMS = [{ to: '', label: 'Quản lý tin tuyển dụng' }]

export default function RecruiterLayout() {
  return <DashboardLayout title="Nhà tuyển dụng" basePath="/recruiter" navItems={NAV_ITEMS} />
}
