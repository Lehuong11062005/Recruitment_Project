import api from './api';

export const jobService = {
  searchJobs: (params = {}) => api.get('/api/v1/jobs', { params }),
  getJobDetail: (jobId) => api.get(`/api/v1/jobs/${jobId}`),
  getRecommendations: () => api.get('/api/v1/jobs/recommendations'),
};