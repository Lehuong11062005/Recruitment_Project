import { Link } from 'react-router-dom';
import Icon from './Icon';

function formatSalary(salary) {
  if (!salary) return 'Thỏa thuận';
  if (typeof salary === 'string') return salary;
  if (salary.min == null && salary.max == null) return 'Thỏa thuận';
  const format = (value) => new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 }).format(Number(value));
  const currency = salary.currency || 'VND';
  if (salary.min != null && salary.max != null) return `${format(salary.min)} – ${format(salary.max)} ${currency}`;
  return salary.min != null ? `Từ ${format(salary.min)} ${currency}` : `Đến ${format(salary.max)} ${currency}`;
}

/**
 * Thẻ việc làm dùng chung (tách từ markup trong JobList.jsx).
 * - badge: node hiển thị cạnh tiêu đề (vd: badge % phù hợp)
 * - footer: node hiển thị dưới hàng meta (vd: tag kỹ năng trùng khớp)
 */
export default function JobCard({ job, badge = null, footer = null }) {
  const id = job.id || job._id;
  return (
    <article className="card catalog-card">
      <div className="company-logo company-logo-large logo-blue">
        {(job.company_name || 'DN').slice(0, 2).toUpperCase()}
      </div>
      <div className="catalog-main">
        <div className="job-title-line">
          <div>
            <strong>{job.title}</strong>
            <span>{job.company_name || 'Doanh nghiệp'}</span>
          </div>
          {badge}
        </div>
        <div className="meta-row">
          <span><Icon name="map" size={15} />{job.location || 'Chưa cập nhật'}</span>
          <span><Icon name="briefcase" size={15} />{job.level || 'MID'}</span>
          <span><Icon name="wallet" size={15} />{formatSalary(job.salary)}</span>
        </div>
        {footer}
      </div>
      <div className="catalog-actions">
        <Link className="btn btn-primary" to={`/candidate/jobs/${id}`}>Xem chi tiết</Link>
      </div>
    </article>
  );
}
