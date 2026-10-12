import api from './api'

// UC-C5 và UC-C7. candidate_id do server lấy từ token, không gửi từ client.
// LƯU Ý: router applications của core-service hiện còn trống nên đường dẫn là GIẢ ĐỊNH.
export const applicationService = {
  // UC-C5: nộp hồ sơ, gửi multipart gồm job_id và file CV (PDF)
  apply(jobId, cvFile) {
    const form = new FormData()
    form.append('job_id', jobId)
    if (cvFile) form.append('cv', cvFile)
    return api.post('/api/v1/applications', form)
  },
  // UC-C7: đơn của tôi, params: { pipeline_status, page, size }
  getMyApplications: (params) => api.get('/api/v1/applications/me', { params }),
  // UC-C7: chi tiết đơn, có pipeline_status và status_history [{ status, changed_by, time }]
  getApplicationById: (applicationId) => api.get(`/api/v1/applications/${applicationId}`),
}
