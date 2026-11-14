import api from './api';

const base = '/api/v1/admin';

export const adminService = {
  getStatistics: () => api.get(`${base}/statistics`),
  listUsers: (params, signal) => api.get(`${base}/users`, { params, signal }),
  listCompanies: (params, signal) => api.get(`${base}/companies`, { params, signal }),
  listJobs: (params, signal) => api.get(`${base}/jobs`, { params, signal }),
  updateUserStatus: (id, status) => api.patch(`${base}/users/${id}/status`, { status }),
  verifyCompany: (id, verification_status) => api.patch(`${base}/companies/${id}/verify`, { verification_status }),
  moderateJob: (id, status) => api.patch(`${base}/jobs/${id}/status`, { status }),
};
