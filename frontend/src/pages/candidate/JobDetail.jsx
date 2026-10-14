import { useParams } from 'react-router-dom'
import PagePlaceholder from '../../components/PagePlaceholder'

// Chi tiết JD + UC-C5: Ứng tuyển. API: jobService.getJobById, applicationService.apply
export default function JobDetail() {
  const { jobId } = useParams()

  return (
    <PagePlaceholder
      code="UC-C5"
      title={`Chi tiết việc làm #${jobId}`}
      description="Xem JD và ứng tuyển bằng CV PDF."
      todo={[
        'Hiển thị thông tin JD',
        'Nút "Ứng tuyển": chọn CV đã lưu hoặc tải file PDF mới',
        'Kiểm tra file: chỉ PDF, giới hạn dung lượng',
        'Xử lý 409 (đã ứng tuyển), tin đã đóng/hết hạn, lỗi upload',
        'Nút "Phân tích độ phù hợp" (UC-C6)',
      ]}
    />
  )
}
