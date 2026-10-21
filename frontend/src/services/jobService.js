import api from './api';
import {
  JOBS_API_CONFIG,
  readJobsSearchParamMap,
} from '../config/env';

const requireJobsEnabled = () => {
  if (!JOBS_API_CONFIG.enabled) {
    throw new Error(
      'API Jobs chưa được bật. Hãy kiểm tra cấu hình router Jobs và các biến môi trường.'
    );
  }
};

const getConfiguredPath = (path, errorMessage) => {
  const normalizedPath = (path || '').trim();

  if (!normalizedPath) {
    throw new Error(errorMessage);
  }

  return normalizedPath;
};

export const jobService = {
  isSearchConfigured() {
    return Boolean(
      JOBS_API_CONFIG.enabled &&
      JOBS_API_CONFIG.listPath &&
      JOBS_API_CONFIG.searchParamMapRaw
    );
  },

  isDetailConfigured() {
    return Boolean(
      JOBS_API_CONFIG.enabled &&
      JOBS_API_CONFIG.detailPathTemplate?.includes('{jobId}')
    );
  },

  searchJobs(filters = {}) {
    requireJobsEnabled();

    const listPath = getConfiguredPath(
      JOBS_API_CONFIG.listPath,
      'Chưa cấu hình VITE_JOBS_LIST_PATH.'
    );

    const map = readJobsSearchParamMap();
    const params = {};

    Object.entries(map).forEach(([frontendKey, backendKey]) => {
      const value = filters[frontendKey];

      if (
        typeof backendKey === 'string' &&
        backendKey.trim() &&
        value !== undefined &&
        value !== null &&
        value !== ''
      ) {
        params[backendKey] = value;
      }
    });

    return api.get(listPath, { params });
  },

  getJobDetail(jobId) {
    requireJobsEnabled();

    const template = getConfiguredPath(
      JOBS_API_CONFIG.detailPathTemplate,
      'Chưa cấu hình VITE_JOBS_DETAIL_PATH_TEMPLATE.'
    );

    if (!template.includes('{jobId}')) {
      throw new Error(
        'VITE_JOBS_DETAIL_PATH_TEMPLATE phải chứa placeholder {jobId}.'
      );
    }

    return api.get(
      template.replace('{jobId}', encodeURIComponent(String(jobId)))
    );
  },

  getRecommendations() {
    requireJobsEnabled();

    const path = getConfiguredPath(
      import.meta.env.VITE_JOBS_RECOMMENDATIONS_PATH,
      'Chưa cấu hình VITE_JOBS_RECOMMENDATIONS_PATH; chưa gửi request.'
    );

    return api.get(path);
  },

  // Recruiter APIs
  getMyJobs() {
    requireJobsEnabled();
    return api.get('/api/v1/jobs/my-jobs');
  },

  createJob(payload) {
    requireJobsEnabled();
    return api.post('/api/v1/jobs', payload);
  },

  updateJob(jobId, payload) {
    requireJobsEnabled();
    return api.put(
      `/api/v1/jobs/${encodeURIComponent(String(jobId))}`,
      payload
    );
  },

  updateJobStatus(jobId, jobStatus) {
    requireJobsEnabled();
    return api.patch(
      `/api/v1/jobs/${encodeURIComponent(String(jobId))}/status`,
      { status: jobStatus }
    );
  },

  // Skills API
  getSkills(params = {}) {
    return api.get('/api/v1/skills', { params });
  },
};