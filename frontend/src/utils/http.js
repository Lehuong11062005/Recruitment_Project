// Lấy thông báo lỗi dễ đọc từ lỗi Axios. FastAPI trả { detail: "..." } hoặc { detail: [{ msg }] } (lỗi 422).
export function getErrorMessage(error, fallback = 'Có lỗi xảy ra, vui lòng thử lại') {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join('; ')
  if (error?.code === 'ERR_NETWORK') return 'Không kết nối được máy chủ (API Gateway chưa chạy?)'
  return error?.message || fallback
}
