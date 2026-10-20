import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import Icon from '../../components/Icon';
import { jobService } from '../../services/jobService';

const formatSalary = (salary) => {
  if (!salary) return 'Thỏa thuận';
  const minimum = Number(salary.min || 0).toLocaleString('vi-VN');
  const maximum = Number(salary.max || 0).toLocaleString('vi-VN');
  return `${minimum} - ${maximum} ${salary.currency || 'VND'}`;
};

export default function LiveJobDetail() {
  const { jobId } = useParams();
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    jobService.getJobDetail(jobId)
      .then((response) => {
        if (active) setJob(response?.data || response);
      })
      .catch((requestError) => {
        if (active) setError(requestError.message || 'Không thể tải thông tin tin tuyển dụng.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [jobId]);

  return (
    <div className="content-stack">
      <Link to="/candidate/jobs" className="inline-link"><Icon name="chevron" size={16} className="back-chevron" /> Quay lại danh sách việc làm</Link>
      {error && <div className="alert-box alert-error" role="alert">{error}</div>}
      {loading && <section className="card empty-state">Đang tải tin tuyển dụng...</section>}
      {!loading && job && (
        <>
          <section className="card job-detail-hero">
            <div className="company-logo company-logo-large logo-blue">{(job.company_name || 'DN').slice(0, 2).toUpperCase()}</div>
            <div className="hero-job-copy">
              <span className="badge badge-blue">Tin tuyển dụng</span>
              <h2 className="display-title">{job.title}</h2>
              <span>{job.company_name || 'Doanh nghiệp'}</span>
            </div>
          </section>
          <section className="card">
            <div className="meta-row">
              <span><Icon name="map" size={15} />{job.location || 'Chưa cập nhật'}</span>
              <span><Icon name="briefcase" size={15} />{job.level || 'MID'}</span>
              <span><Icon name="wallet" size={15} />{formatSalary(job.salary)}</span>
              <span><Icon name="clock" size={15} />Kinh nghiệm: {job.experience_required || 0} năm</span>
            </div>
            <h3 className="section-title">Mô tả công việc</h3>
            <div className="job-description-content">{job.description}</div>
          </section>
          <section className="card">
            <div className="card-header">
              <div><h3 className="section-title">Kỹ năng yêu cầu</h3><p className="muted small">Các kỹ năng được nhà tuyển dụng đề cập.</p></div>
            </div>
            <p className="muted small">{Array.isArray(job.required_skill_names) && job.required_skill_names.length ? job.required_skill_names.join(', ') : 'Nhà tuyển dụng chưa chỉ định kỹ năng.'}</p>
          </section>
        </>
      )}
      {!loading && !job && !error && <section className="card empty-state"><strong>Không tìm thấy tin tuyển dụng</strong><p>Tin này không còn mở hoặc đã được gỡ khỏi hệ thống.</p></section>}
    </div>
  );
}
