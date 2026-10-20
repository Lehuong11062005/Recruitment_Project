import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import Icon from '../../components/Icon';
import { jobService } from '../../services/jobService';

export default function JobList() {
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
            <input
              type="search"
              aria-label="Từ khóa việc làm"
              placeholder="Tiêu đề hoặc công ty"
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
            />
          </label>
          <label className="search-input">
            <Icon name="map" size={17} />
            <input
              type="search"
              aria-label="Địa điểm"
              placeholder="Địa điểm"
              value={location}
              onChange={(event) => setLocation(event.target.value)}
            />
          </label>
          <button className="btn btn-primary" type="button">
            <Icon name="search" size={16} /> Tìm kiếm
          </button>
        </form>
      </section>

      <div className="result-toolbar">
        <strong>{visibleJobs.length} vị trí phù hợp</strong>
        <span className="muted">{loading ? 'Đang tải việc làm...' : 'Tin đang tuyển dụng từ máy chủ'}</span>
      </div>

      {error && <div className="alert-box alert-error" role="alert">{error}</div>}
      <div className="job-catalog">
        {visibleJobs.map((job) => (
          <article className="card catalog-card" key={job.id}>
            <div className="company-logo company-logo-large logo-blue">
              {(job.company_name || 'DN').slice(0, 2).toUpperCase()}
            </div>
            <div className="catalog-main">
              <div className="job-title-line">
                <div>
                  <strong>{job.title}</strong>
                  <span>{job.company_name}</span>
                </div>
              </div>
              <div className="meta-row">
                <span><Icon name="map" size={15} />{job.location || 'Chưa cập nhật'}</span>
                <span><Icon name="briefcase" size={15} />{job.level || 'MID'}</span>
                <span><Icon name="wallet" size={15} />{job.salary
                  ? `${Number(job.salary.min || 0).toLocaleString('vi-VN')} - ${Number(job.salary.max || 0).toLocaleString('vi-VN')} ${job.salary.currency || 'VND'}`
                  : 'Thỏa thuận'}</span>
              </div>
            </div>
            <div className="catalog-actions">
              <Link className="btn btn-primary" to={`/candidate/jobs/${job.id}`}>Xem chi tiết</Link>
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
