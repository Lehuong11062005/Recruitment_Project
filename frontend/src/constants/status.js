// Trạng thái đơn ứng tuyển: applications.pipeline_status (UC-C7)
export const PIPELINE_STATUS = {
  APPLIED: { label: 'Đã nộp', color: 'bg-slate-100 text-slate-700' },
  SCREENING: { label: 'Đang sàng lọc', color: 'bg-blue-100 text-blue-700' },
  INTERVIEW: { label: 'Phỏng vấn', color: 'bg-amber-100 text-amber-700' },
  REJECTED: { label: 'Không phù hợp', color: 'bg-red-100 text-red-700' },
  HIRED: { label: 'Trúng tuyển', color: 'bg-green-100 text-green-700' },
}
