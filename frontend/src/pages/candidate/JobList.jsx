import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { CANDIDATE_DEMO_MODE } from '../../config/env';
import { DEMO_JOBS } from '../../data/candidateDemo';
import { jobService } from '../../services/jobService';
import Icon from '../../components/Icon';
const PAGE_SIZE = 6;
const EMPTY_FILTERS = { keyword: '', location: '', level: '', salaryMin: '', salaryMax: '' };
const errorText = (error) => error?.message || 'Không thể tải dữ liệu việc làm.';

function formatSalary(salary) {
  if (!salary) return 'Thỏa thuận';
  if (typeof salary === 'string') return salary;
  if (salary.min == null && salary.max == null) return 'Thỏa thuận';
  const format = (value) => new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 }).format(Number(value));
  const currency = salary.currency || 'VND';
  if (salary.min != null && salary.max != null) return `${format(salary.min)} – ${format(salary.max)} ${currency}`;
  return salary.min != null ? `Từ ${format(salary.min)} ${currency}` : `Đến ${format(salary.max)} ${currency}`;
}

function normalizeJob(job) {
  return {
    ...job,
    id: String(job.id ?? job._id ?? job.job_id ?? ''),
    title: job.title || 'Tin tuyển dụng chưa có tiêu đề',
    company_name: job.company_name || job.company?.name || job.company?.company_name || '',
    location: job.location || 'Chưa cập nhật địa điểm',
    isDemo: Boolean(job.isDemo),
  };
}

function extractJobs(response) {
  const payload = response?.data ?? response;
  if (Array.isArray(payload)) return { jobs: payload, total: payload.length };
  const jobs = payload?.items ?? payload?.jobs ?? payload?.results;
  if (!Array.isArray(jobs)) throw new Error('Response API Jobs chưa có dạng danh sách được giao diện hỗ trợ; hãy thống nhất schema với backend.');
  const rawTotal = payload.total ?? payload.total_count ?? payload.count ?? jobs.length;
  const total = Number(rawTotal);
  return { jobs, total: Number.isFinite(total) ? total : jobs.length };
}

function filterDemoJobs(filters) {
  const keyword = filters.keyword.trim().toLocaleLowerCase('vi-VN');
  const location = filters.location.trim().toLocaleLowerCase('vi-VN');
  const min = filters.salaryMin === '' ? null : Number(filters.salaryMin);
  const max = filters.salaryMax === '' ? null : Number(filters.salaryMax);
  return DEMO_JOBS.filter((job) => {
    if (`${job.title} ${job.company_name} ${job.description}`.toLocaleLowerCase('vi-VN').includes(keyword) === false && keyword) return false;
    if (location && !job.location.toLocaleLowerCase('vi-VN').includes(location)) return false;
    if (filters.level && filters.level !== job.level) return false;
    if (min !== null && job.salary?.max != null && Number(job.salary.max) < min) return false;
    if (max !== null && job.salary?.min != null && Number(job.salary.min) > max) return false;
    return true;
  });
}

export default function JobList() {
  const [formFilters, setFormFilters] = useState(EMPTY_FILTERS);
  const [activeFilters, setActiveFilters] = useState(EMPTY_FILTERS);
  const [jobs, setJobs] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(!CANDIDATE_DEMO_MODE && jobService.isSearchConfigured());
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [validationError, setValidationError] = useState('');
  const [isDemoResults, setIsDemoResults] = useState(false);
  const [apiUnavailable, setApiUnavailable] = useState(
    !CANDIDATE_DEMO_MODE && !jobService.isSearchConfigured()
  );

  useEffect(() => {
    let active = true;
    Promise.resolve().then(async () => {
      if (!active) return;
      setError('');
      if (CANDIDATE_DEMO_MODE) {
        const filtered = filterDemoJobs(activeFilters);
        const start = (page - 1) * PAGE_SIZE;
        setJobs(filtered.slice(start, start + PAGE_SIZE).map(normalizeJob));
        setTotal(filtered.length);
        setIsDemoResults(true);
        setApiUnavailable(false);
        setNotice('DỮ LIỆU DEMO: đây là dữ liệu và thao tác minh họa, không phải dữ liệu backend.');
        setLoading(false);
        return;
      }
      if (!jobService.isSearchConfigured()) {
        setJobs([]);
        setTotal(0);
        setIsDemoResults(false);
        setApiUnavailable(true);
        setNotice('');
        setLoading(false);
        return;
      }
      setApiUnavailable(false);
      setLoading(true);
      try {
        const result = extractJobs(await jobService.searchJobs({
          keyword: activeFilters.keyword.trim(),
          location: activeFilters.location.trim(),
          level: activeFilters.level,
          salaryMin: activeFilters.salaryMin,
          salaryMax: activeFilters.salaryMax,
          page,
          size: PAGE_SIZE,
        }));
        if (!active) return;
        const available = result.jobs.filter((job) => (!job.status || job.status === 'OPEN') && !job.deleted_at);
        setJobs(available.map((job) => normalizeJob({ ...job, isDemo: false })));
        setTotal(result.total);
        setIsDemoResults(false);
        setNotice('');
      } catch (loadError) {
        if (!active) return;
        setJobs([]);
        setTotal(0);
        setError(errorText(loadError));
      } finally {
        if (active) setLoading(false);
      }
    });
    return () => { active = false; };
  }, [activeFilters, page]);

  const pageCount = useMemo(() => Math.max(1, Math.ceil(total / PAGE_SIZE)), [total]);

  const updateField = (event) => {
    const { name, value } = event.target;
    setFormFilters((current) => ({ ...current, [name]: value }));
  };

  const submitSearch = (event) => {
    event.preventDefault();
    if (!CANDIDATE_DEMO_MODE && !jobService.isSearchConfigured()) return;
    setValidationError('');
    if (formFilters.salaryMin !== '' && Number(formFilters.salaryMin) < 0) {
      setValidationError('Lương tối thiểu không được âm.');
      return;
    }
    if (formFilters.salaryMax !== '' && Number(formFilters.salaryMax) < 0) {
      setValidationError('Lương tối đa không được âm.');
      return;
    }
    if (formFilters.salaryMin !== '' && formFilters.salaryMax !== '' && Number(formFilters.salaryMin) > Number(formFilters.salaryMax)) {
      setValidationError('Lương tối thiểu không được lớn hơn lương tối đa.');
      return;
    }
    setError('');
    setPage(1);
    if (!CANDIDATE_DEMO_MODE && jobService.isSearchConfigured()) setLoading(true);
    setActiveFilters({ ...formFilters });
  };

  return (
    <div className="content-stack">
      <section className="card space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div><span className="badge badge-blue">UC-C4</span><h2 className="mt-2 text-2xl font-bold">Tìm kiếm việc làm</h2><p className="muted mt-1">Tìm theo từ khóa, địa điểm, cấp độ và mức lương.</p></div>
          {isDemoResults && <span className="badge badge-amber">DỮ LIỆU DEMO</span>}
        </div>
        <form onSubmit={submitSearch} className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
          <label className="block xl:col-span-2"><span className="mb-1 block text-xs font-semibold">Từ khóa</span><input name="keyword" value={formFilters.keyword} onChange={updateField} placeholder="Tiêu đề, công ty, công nghệ" className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm" /></label>
          <label className="block"><span className="mb-1 block text-xs font-semibold">Địa điểm</span><input name="location" value={formFilters.location} onChange={updateField} placeholder="Hà Nội" className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm" /></label>
          <label className="block"><span className="mb-1 block text-xs font-semibold">Cấp độ</span><select name="level" value={formFilters.level} onChange={updateField} className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm"><option value="">Tất cả</option><option value="JUNIOR">Junior</option><option value="MID">Middle</option><option value="SENIOR">Senior</option></select></label>
          <label className="block"><span className="mb-1 block text-xs font-semibold">Lương từ</span><input name="salaryMin" type="number" min="0" value={formFilters.salaryMin} onChange={updateField} placeholder="Tối thiểu" className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm" /></label>
          <label className="block"><span className="mb-1 block text-xs font-semibold">Lương đến</span><input name="salaryMax" type="number" min="0" value={formFilters.salaryMax} onChange={updateField} placeholder="Tối đa" className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm" /></label>
          <div className="flex flex-wrap items-center gap-2 md:col-span-2 xl:col-span-6"><button type="submit" className="btn btn-primary" disabled={!CANDIDATE_DEMO_MODE && !jobService.isSearchConfigured()}><Icon name="search" size={16} />Tìm kiếm</button><button type="button" onClick={() => { setFormFilters(EMPTY_FILTERS); setActiveFilters(EMPTY_FILTERS); setPage(1); setValidationError(''); setError(''); }} className="btn btn-secondary">Xóa bộ lọc</button>{validationError && <span role="alert" className="text-sm text-red-700">{validationError}</span>}</div>
        </form>
      </section>

      {notice && <div role="status" className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900"><strong className="block">Lưu ý về nguồn dữ liệu</strong><span className="mt-1 block">{notice}</span></div>}
      {apiUnavailable && <div role="status" className="api-unavailable"><strong>API Jobs chưa khả dụng</strong><span>API đang tắt hoặc thiếu cấu hình endpoint/query. Danh sách được để trống; không thay bằng dữ liệu demo.</span></div>}
      {error && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"><strong className="block">Không tải được việc làm</strong><span className="mt-1 block">{error}</span></div>}

      <div className="result-toolbar"><strong>{loading ? 'Đang tải việc làm…' : apiUnavailable ? 'Danh sách chưa khả dụng' : `${total} vị trí phù hợp`}</strong>{!apiUnavailable && <span className="muted small">Trang {page} / {pageCount}</span>}</div>
      {loading ? <section className="card text-center text-slate-500">Đang tải danh sách việc làm…</section> : jobs.length ? (
        <div className="grid gap-4">
          {jobs.map((job) => <article className="card" key={job.id}>
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><h3 className="text-lg font-bold text-slate-900">{job.title}</h3>{job.isDemo && <span className="badge badge-amber">DỮ LIỆU DEMO</span>}</div><p className="mt-1 text-sm font-semibold text-slate-600">{job.company_name || 'Nhà tuyển dụng chưa cập nhật'}</p>
                <div className="mt-3 flex flex-wrap gap-2 text-xs"><span className="badge badge-gray"><Icon name="map" size={13} />{job.location || 'Chưa cập nhật'}</span>{job.level && <span className="badge badge-blue">{job.level}</span>}<span className="badge badge-green"><Icon name="wallet" size={13} />{formatSalary(job.salary)}</span></div>
                {job.description && <p className="muted mt-3 line-clamp-2 text-sm">{job.description}</p>}
              </div>
              <Link className="btn btn-primary shrink-0" to={`/candidate/jobs/${encodeURIComponent(job.id)}`}>Xem chi tiết<Icon name="chevron" size={15} /></Link>
            </div>
          </article>)}
        </div>
      ) : !apiUnavailable && !error ? <section className="card text-center"><Icon name="search" size={28} /><h3 className="mt-2 font-bold">Không tìm thấy việc làm phù hợp</h3><p className="muted mt-1">Thử thay đổi từ khóa hoặc địa điểm tìm kiếm.</p></section> : null}

      {!apiUnavailable && pageCount > 1 && <div className="flex items-center justify-center gap-3"><button type="button" disabled={page <= 1 || loading} onClick={() => { if (jobService.isSearchConfigured()) setLoading(true); setPage((value) => value - 1); }} className="btn btn-secondary disabled:opacity-40">Trang trước</button><span className="muted small">{page}/{pageCount}</span><button type="button" disabled={page >= pageCount || loading} onClick={() => { if (jobService.isSearchConfigured()) setLoading(true); setPage((value) => value + 1); }} className="btn btn-secondary disabled:opacity-40">Trang sau</button></div>}
    </div>
  );
}

export function LiveJobList() {
  const [keyword, setKeyword] = useState('');
  const [location, setLocation] = useState('');
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    jobService.searchJobs()
      .then((response) => {
        const items = Array.isArray(response) ? response : response?.data;
        if (active) setJobs(Array.isArray(items) ? items : []);
      })
      .catch((requestError) => {
        if (active) setError(requestError.message || 'Không thể tải danh sách việc làm.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const visibleJobs = useMemo(() => jobs.filter((job) => (
    `${job.title || ''} ${job.company_name || ''}`
      .toLocaleLowerCase('vi')
      .includes(keyword.trim().toLocaleLowerCase('vi'))
    && (job.location || '').toLocaleLowerCase('vi')
      .includes(location.trim().toLocaleLowerCase('vi'))
  )), [jobs, keyword, location]);

  const formatLiveSalary = (salary) => {
    if (!salary) return 'Thỏa thuận';
    const minimum = Number(salary.min || 0).toLocaleString('vi-VN');
    const maximum = Number(salary.max || 0).toLocaleString('vi-VN');
    return `${minimum} - ${maximum} ${salary.currency || 'VND'}`;
  };

  return (
    <div className="content-stack">
      <section className="card filter-card">
        <div className="filter-title">
          <Icon name="filter" />
          <strong>Bộ lọc việc làm</strong>
          <span>Tìm theo vị trí, công ty hoặc địa điểm.</span>
        </div>
        <form className="job-search-grid" onSubmit={(event) => event.preventDefault()}>
          <label className="search-input">
            <Icon name="search" size={17} />
            <input type="search" aria-label="Từ khóa việc làm" placeholder="Tiêu đề hoặc công ty" value={keyword} onChange={(event) => setKeyword(event.target.value)} />
          </label>
          <label className="search-input">
            <Icon name="map" size={17} />
            <input type="search" aria-label="Địa điểm" placeholder="Địa điểm" value={location} onChange={(event) => setLocation(event.target.value)} />
          </label>
          <button className="btn btn-primary" type="submit"><Icon name="search" size={16} /> Tìm kiếm</button>
        </form>
      </section>

      {error && <div className="alert-box alert-error" role="alert">{error}</div>}
      <div className="result-toolbar">
        <strong>{visibleJobs.length} vị trí phù hợp</strong>
        <span className="muted">{loading ? 'Đang tải việc làm...' : 'Tin đang tuyển dụng từ máy chủ'}</span>
      </div>
      <div className="job-catalog">
        {visibleJobs.map((job) => (
          <article className="card catalog-card" key={job.id || job._id}>
            <div className="company-logo company-logo-large logo-blue">{(job.company_name || 'DN').slice(0, 2).toUpperCase()}</div>
            <div className="catalog-main">
              <div className="job-title-line">
                <div><strong>{job.title}</strong><span>{job.company_name || 'Doanh nghiệp'}</span></div>
              </div>
              <div className="meta-row">
                <span><Icon name="map" size={15} />{job.location || 'Chưa cập nhật'}</span>
                <span><Icon name="briefcase" size={15} />{job.level || 'MID'}</span>
                <span><Icon name="wallet" size={15} />{formatLiveSalary(job.salary)}</span>
              </div>
            </div>
            <div className="catalog-actions">
              <Link className="btn btn-primary" to={`/candidate/jobs/${job.id || job._id}`}>Xem chi tiết</Link>
            </div>
          </article>
        ))}
        {!loading && !error && visibleJobs.length === 0 && (
          <section className="card empty-state">
            <Icon name="search" size={26} />
            <strong>Không tìm thấy việc làm phù hợp</strong>
            <p>Hiện chưa có tin đang tuyển dụng phù hợp với bộ lọc.</p>
          </section>
        )}
      </div>
    </div>
  );
}