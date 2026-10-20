export const MOCK_AUTH = import.meta.env.VITE_MOCK_AUTH === 'true';
// Giữ tương thích với API/WS config hiện có trong nhánh main.
export const API_URL = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const WS_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000';

// true chỉ dùng để xem dữ liệu/kết quả mô phỏng trên giao diện; không lưu vào backend.
export const CANDIDATE_DEMO_MODE = import.meta.env.VITE_CANDIDATE_DEMO_MODE === 'true';

// Router Jobs hiện trống trong main, vì vậy chỉ gọi sau khi backend xác nhận xong.
export const JOBS_API_CONFIG = {
  enabled: import.meta.env.VITE_JOBS_API_ENABLED === 'true',
  listPath: (import.meta.env.VITE_JOBS_LIST_PATH || '').trim(),
  detailPathTemplate: (import.meta.env.VITE_JOBS_DETAIL_PATH_TEMPLATE || '').trim(),
  searchParamMapRaw: (import.meta.env.VITE_JOBS_SEARCH_PARAM_MAP || '').trim(),
};

export function readJobsSearchParamMap() {
  if (!JOBS_API_CONFIG.searchParamMapRaw) {
    throw new Error('Chưa cấu hình VITE_JOBS_SEARCH_PARAM_MAP theo query parameters đã được backend xác nhận.');
  }
  try {
    const parsed = JSON.parse(JOBS_API_CONFIG.searchParamMapRaw);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('invalid map');
    return parsed;
  } catch {
    throw new Error('VITE_JOBS_SEARCH_PARAM_MAP phải là JSON object hợp lệ.');
  }
}
