import api from './api'

// UC-C4: Tìm kiếm việc làm.
// LƯU Ý: router jobs của core-service hiện còn trống nên các đường dẫn/tham số dưới đây là GIẢ ĐỊNH,
// khi backend xong thì đối chiếu và sửa lại.
// params: { keyword, location, salary_min, salary_max, page, size }
export const jobService = {
  searchJobs: (params) => api.get('/api/v1/jobs', { params }),
  getJobById: (jobId) => api.get(`/api/v1/jobs/${jobId}`),
}
