import { useParams } from 'react-router-dom'
import PagePlaceholder from '../../components/PagePlaceholder'

// UC-C7: chi tiết đơn + lịch sử trạng thái. API: applicationService.getApplicationById
export default function ApplicationDetail() {
  const { applicationId } = useParams()

  return (
    <PagePlaceholder
      code="UC-C7"
      title={`Chi tiết đơn ứng tuyển #${applicationId}`}
      todo={[
        'Thông tin job + trạng thái hiện tại',
        'Dòng thời gian từ status_history ({ status, changed_by, time })',
        'Xử lý 403 (đơn không thuộc ứng viên)',
        'Nút "Nhắn tin" sang UC-C8, nút xem điểm AI (UC-C6)',
      ]}
    />
  )
}
