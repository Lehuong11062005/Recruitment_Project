import api from './api';

export const applicationService = {
  applyJob: (jobId, file) => {
    const formData = new FormData();
    formData.append('job_id', jobId);
    if (file) {
      formData.append('file', file);
    }
    return api.post('/api/v1/applications', formData);
  },
  getMyApplications: (params = {}) => api.get('/api/v1/applications/me', { params }),
  getApplicationDetail: (applicationId) => api.get(`/api/v1/applications/${applicationId}`),
};