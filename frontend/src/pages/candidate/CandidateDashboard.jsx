import { Link } from 'react-router-dom'
import PagePlaceholder from '../../components/PagePlaceholder'

export default function CandidateDashboard() {
  return (
    <div className="space-y-4">
      <PagePlaceholder
        title="Trang chủ ứng viên"
        description="Khu vực 'Việc làm phù hợp với bạn' (UC-Bổ sung 2: gợi ý việc làm) sẽ nằm ở đây."
      />
      <div className="flex gap-3 text-sm">
        <Link to="/candidate/jobs" className="text-blue-600 hover:underline">Tìm việc làm</Link>
        <Link to="/candidate/applications" className="text-blue-600 hover:underline">Đơn ứng tuyển</Link>
        <Link to="/candidate/messages" className="text-blue-600 hover:underline">Tin nhắn</Link>
      </div>
    </div>
  )
}
