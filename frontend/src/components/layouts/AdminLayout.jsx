import DashboardLayout from './DashboardLayout'

const NAV_ITEMS = [{ to: '', label: 'Thống kê' }]

export default function AdminLayout() {
  return <DashboardLayout title="Quản trị" basePath="/admin" navItems={NAV_ITEMS} />
}
