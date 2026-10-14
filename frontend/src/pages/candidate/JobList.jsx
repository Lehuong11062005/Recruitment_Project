import { useState } from 'react';
import { Link } from 'react-router-dom';

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

  return (
    <div>
      <h1 style={{ fontSize: '22px', fontWeight: 700, color: '#142B4A', marginBottom: '16px' }}>
        Tìm kiếm việc làm (UC-C4)
      </h1>

      <div
        style={{
          backgroundColor: '#FFFFFF',
          border: '1px solid #DCE5F0',
          borderRadius: '12px',
          padding: '20px',
          marginBottom: '20px',
          display: 'grid',
          gridTemplateColumns: '2fr 1fr auto',
          gap: '12px',
        }}
      >
        <input
          type="text"
          className="form-input"
          placeholder="Nhập từ khóa công việc, kỹ năng (VD: Python, ReactJS)..."
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
        />
        <input
          type="text"
          className="form-input"
          placeholder="Địa điểm (VD: Hà Nội)"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
        />
        <button type="button" className="btn-primary" style={{ padding: '0 24px', height: '42px' }}>
          Tìm kiếm
        </button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {MOCK_JOBS.map((job) => (
          <div
            key={job.id}
            style={{
              backgroundColor: '#FFFFFF',
              border: '1px solid #DCE5F0',
              borderRadius: '12px',
              padding: '20px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <div>
              <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#142B4A' }}>{job.title}</h3>
              <p style={{ fontSize: '14px', color: '#64748B', marginTop: '4px' }}>
                {job.company_name} • {job.location} • Cấp bậc: {job.level}
              </p>
              <p style={{ fontSize: '14px', fontWeight: 600, color: '#155EEF', marginTop: '6px' }}>
                Mức lương: {job.salary}
              </p>
            </div>
            <Link
              to={`/candidate/jobs/${job.id}`}
              style={{
                padding: '10px 16px',
                backgroundColor: '#155EEF',
                color: '#FFFFFF',
                borderRadius: '8px',
                fontSize: '14px',
                fontWeight: 600,
              }}
            >
              Xem chi tiết & Ứng tuyển
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
}