import PagePlaceholder from '../../components/PagePlaceholder'

// UC-C4: Tìm kiếm việc làm. API: jobService.searchJobs(params)
export default function JobList() {
  return (
    <PagePlaceholder
      code="UC-C4"
      title="Tìm kiếm việc làm"
      description="Tìm tin tuyển dụng theo từ khóa, mức lương, địa điểm."
      todo={[
        'Form tiêu chí: từ khóa, lương tối thiểu/tối đa, địa điểm',
        'Kiểm tra dữ liệu: lương tối thiểu không lớn hơn lương tối đa',
        'Danh sách job (title, location, salary { min, max, currency }, level) + phân trang phía server',
        'Trạng thái: đang tải, không có kết quả, lỗi',
        'Bấm vào job để sang /candidate/jobs/:jobId',
      ]}
    />
  )
}
