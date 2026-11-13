import { useEffect, useState } from 'react';
import Icon from '../../components/Icon';
import { PIPELINE_STATUS_LABELS } from '../../constants/status';
import { adminService } from '../../services/adminService';

const formatNumber = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 2 });
const SCORE_BUCKETS = [
  ['under_50', 'Dưới 50%'],
  ['from_50_to_75', '50–75%'],
  ['over_75', 'Trên 75%'],
];

function Breakdown({ title, values }) {
  const max = Math.max(1, ...values.map(([, count]) => count));
  return (
    <section className="card admin-breakdown">
      <h2 className="section-title">{title}</h2>
      {values.length === 0 ? <p className="muted">Chưa có dữ liệu.</p> : (
        <ul>
          {values.map(([label, count]) => (
            <li key={label}>
              <div><span>{label}</span><strong>{formatNumber.format(count)}</strong></div>
              <div className="admin-bar" aria-hidden="true"><span style={{ width: `${count / max * 100}%` }} /></div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    let active = true;
    adminService.getStatistics()
      .then((data) => { if (active) setStats(data); })
      .catch((failure) => { if (active) setError(failure.message); });
    return () => { active = false; };
  }, [revision]);

  if (error) return (
    <section className="card">
      <p className="alert-box alert-error" role="alert">{error}</p>
      <button type="button" className="btn btn-secondary" onClick={() => {
        setError('');
        setRevision((value) => value + 1);
      }}>Thử lại</button>
    </section>
  );
  if (!stats) return <section className="card" role="status">Đang tải thống kê…</section>;

  const { users, companies, jobs, applications, ai_matching: ai } = stats;
  const cards = [
    ['Người dùng', users.total, 'users', `${users.candidates} ứng viên · ${users.recruiters} nhà tuyển dụng · ${users.admins} quản trị viên`],
    ['Doanh nghiệp', companies.total, 'building', `${companies.pending} chờ duyệt · ${companies.verified} đã duyệt · ${companies.rejected} từ chối`],
    ['Tin tuyển dụng', jobs.total, 'briefcase', `${jobs.open} đang tuyển · ${jobs.closed} đã đóng · ${jobs.hidden} đã ẩn`],
    ['Đơn ứng tuyển', applications.total, 'file', `${ai.total_scored} đơn có điểm AI`],
  ];
  return (
    <div className="content-stack">
      <div className="stats-grid">
        {cards.map(([label, value, icon, detail]) => (
          <section className="card stat-card" key={label}>
            <span className="stat-icon"><Icon name={icon} /></span>
            <div><h2>{label}</h2><div className="stat-value">{formatNumber.format(value)}</div><small className="muted">{detail}</small></div>
          </section>
        ))}
      </div>
      <div className="admin-charts">
        <Breakdown title="Tiến độ tuyển dụng" values={Object.entries(applications.by_pipeline_status).map(
          ([status, count]) => [PIPELINE_STATUS_LABELS[status] || status, count],
        )} />
        <Breakdown
          title={ai.total_scored ? `Phân bố điểm AI · Trung bình ${formatNumber.format(ai.average_score)}%` : 'Phân bố điểm AI'}
          values={SCORE_BUCKETS.map(([key, label]) => [label, ai.score_distribution[key] ?? 0])}
        />
        <Breakdown title="Hồ sơ theo phiên bản AI" values={Object.entries(ai.by_matching_version)} />
      </div>
    </div>
  );
}
