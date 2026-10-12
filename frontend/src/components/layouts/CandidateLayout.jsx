import DashboardLayout from './DashboardLayout'

const NAV_ITEMS = [
  { to: '', label: 'Trang chủ' },
  { to: '/jobs', label: 'Việc làm' }, // UC-C4
  { to: '/applications', label: 'Đơn ứng tuyển' }, // UC-C5, C7
  { to: '/messages', label: 'Tin nhắn' }, // UC-C8
]

export default function CandidateLayout() {
  return <DashboardLayout title="Ứng viên" basePath="/candidate" navItems={NAV_ITEMS} />
}
