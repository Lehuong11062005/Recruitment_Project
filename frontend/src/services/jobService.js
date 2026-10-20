import api from './api';
import { JOBS_API_CONFIG, readJobsSearchParamMap } from '../config/env';

const requireJobsEnabled = () => {
  if (!JOBS_API_CONFIG.enabled) {
    throw new Error('API Jobs chưa được bật vì router Jobs trong repository hiện chưa có xử lý đã xác nhận.');
  }
};

export const jobService = {
  isSearchConfigured() {
    return Boolean(JOBS_API_CONFIG.enabled && JOBS_API_CONFIG.listPath && JOBS_API_CONFIG.searchParamMapRaw);
  },
  isDetailConfigured() {
    return Boolean(JOBS_API_CONFIG.enabled && JOBS_API_CONFIG.detailPathTemplate.includes('{jobId}'));
  },
  searchJobs(filters = {}) {
    requireJobsEnabled();
    if (!JOBS_API_CONFIG.listPath) throw new Error('Chưa cấu hình VITE_JOBS_LIST_PATH theo endpoint đã xác nhận.');
    const map = readJobsSearchParamMap();
    const params = {};
    Object.entries(map).forEach(([frontendKey, backendKey]) => {
      const value = filters[frontendKey];
      if (typeof backendKey === 'string' && backendKey.trim() && value !== undefined && value !== null && value !== '') {
        params[backendKey] = value;
      }
    });
    return api.get(JOBS_API_CONFIG.listPath, { params });
  },
  getJobDetail(jobId) {
    requireJobsEnabled();
    const template = JOBS_API_CONFIG.detailPathTemplate;
    if (!template.includes('{jobId}')) throw new Error('Chưa cấu hình VITE_JOBS_DETAIL_PATH_TEMPLATE với placeholder {jobId}.');
    return api.get(template.replace('{jobId}', encodeURIComponent(jobId)));
  },
  getRecommendations() {
    const path = (import.meta.env.VITE_JOBS_RECOMMENDATIONS_PATH || '').trim();
    if (!path) throw new Error('API gợi ý việc làm chưa được xác nhận; chưa gửi request.');
    return api.get(path);
  },
};
