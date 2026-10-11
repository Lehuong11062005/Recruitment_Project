import PagePlaceholder from '../../components/PagePlaceholder'

// UC-C7: Theo dõi trạng thái ứng tuyển. API: applicationService.getMyApplications
// Trạng thái dùng pipeline_status (xem src/constants/status.js)
export default function MyApplications() {
  return (
    <PagePlaceholder
      code="UC-C7"
      title="Đơn ứng tuyển của tôi"
      description="Xem lịch sử nộp đơn và theo dõi trạng thái theo thời gian thực."
      todo={[
        'Danh sách đơn + pipeline_status (APPLIED, SCREENING, INTERVIEW, REJECTED, HIRED) + phân trang',
        'Lọc theo trạng thái',
        'Kết nối WebSocket, nhận sự kiện đổi trạng thái để cập nhật ngay',
        'Mất kết nối thì tự kết nối lại và tải lại dữ liệu',
        'Bấm vào đơn để sang /candidate/applications/:applicationId',
      ]}
    />
  )
}
