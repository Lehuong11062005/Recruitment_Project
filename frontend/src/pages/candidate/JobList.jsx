import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import Icon from '../../components/Icon';

const MOCK_JOBS = [
  {
    id: '6610a1000000000000000001',
    title: 'Backend Developer (Python / FastAPI)',
    company_name: 'FPT Software',
    location: 'Hà Nội',
    level: 'MID',
    salary: '20 - 35 triệu VND',
  },
  {
    id: '6610a1000000000000000002',
    title: 'Frontend Engineer (ReactJS)',
    company_name: 'VNG Corporation',
    location: 'TP. Hồ Chí Minh',
    level: 'JUNIOR',
    salary: '15 - 25 triệu VND',
  },
];

export default function JobList() {
  const [keyword, setKeyword] = useState('');
  const [location, setLocation] = useState('');
  const jobs = useMemo(() => MOCK_JOBS.filter((job) => (
    `${job.title} ${job.company_name}`.toLowerCase().includes(keyword.trim().toLowerCase())
    && job.location.toLowerCase().includes(location.trim().toLowerCase())
  )), [keyword, location]);

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
        <strong>{jobs.length} vị trí phù hợp</strong>
        <span className="muted">Kết quả khớp với bộ lọc</span>
      </div>

      <div className="job-catalog">
        <div className="demo-disclaimer">
          <Icon name="warning" size={15} />
          <span>Danh sách hiện tại dùng các dữ liệu mẫu đã có trong frontend.</span>
        </div>
        {jobs.map((job) => (
          <article className="card catalog-card" key={job.id}>
            <div className="company-logo company-logo-large logo-blue">
              {job.company_name.slice(0, 2).toUpperCase()}
            </div>
            <div className="catalog-main">
              <div className="job-title-line">
                <div>
                  <strong>{job.title}</strong>
                  <span>{job.company_name}</span>
                </div>
              </div>
              <div className="meta-row">
                <span><Icon name="map" size={15} />{job.location}</span>
                <span><Icon name="briefcase" size={15} />{job.level}</span>
                <span><Icon name="wallet" size={15} />{job.salary}</span>
              </div>
            </div>
            <div className="catalog-actions">
              <Link className="btn btn-primary" to={`/candidate/jobs/${job.id}`}>Xem chi tiết</Link>
            </div>
          </article>
        ))}
        {jobs.length === 0 && (
          <section className="card empty-state">
            <Icon name="search" size={26} />
            <strong>Không tìm thấy việc làm phù hợp</strong>
            <p>Thử thay đổi từ khóa hoặc địa điểm tìm kiếm.</p>
          </section>
        )}
      </div>
    </div>
  );
}
