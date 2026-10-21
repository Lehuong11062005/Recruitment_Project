import api from './api';

export const jobService = {
  searchJobs: (params = {}) => api.get('/api/v1/jobs', { params }),
  getJobDetail: (jobId) => api.get(`/api/v1/jobs/${jobId}`),
  getRecommendations: () => api.get('/api/v1/jobs/recommendations'),
  getMyJobs: () => api.get('/api/v1/jobs/mine'),
  createJob: (payload) => api.post('/api/v1/jobs/managed', payload),
  updateJob: (jobId, payload) => api.put(`/api/v1/jobs/managed/${jobId}`, payload),
  updateJobStatus: (jobId, status) => api.patch(`/api/v1/jobs/managed/${jobId}/status`, { status }),
  getSkills: (params = {}) => api.get('/api/v1/skills', { params }),
};