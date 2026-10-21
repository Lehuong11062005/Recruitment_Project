import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { PIPELINE_STATUS, PIPELINE_STATUS_LABELS } from '../../constants/status';
import { applicationService } from '../../services/applicationService';

const statusTone = {
  [PIPELINE_STATUS.APPLIED]: '',
  [PIPELINE_STATUS.SCREENING]: 'warning',
  [PIPELINE_STATUS.INTERVIEW]: '',
  [PIPELINE_STATUS.HIRED]: 'success',
  [PIPELINE_STATUS.REJECTED]: 'danger',
};

export default function MyApplications() {
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    applicationService.getMyApplications()
      .then((result) => {
        if (!active) return;
        const rows = result?.items ?? result;
        if (!Array.isArray(rows)) throw new Error('Danh sách đơn ứng tuyển không đúng định dạng.');
        setApplications(rows);
      })
      .catch((requestError) => {
        if (active) setError(requestError.message || 'Không thể tải danh sách đơn ứng tuyển.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, []);

  return (
    <div className="content-stack">
      <section className="card">
        <div className="card-header">
          <div>
            <h2 className="section-title">Danh sách đơn ứng tuyển</h2>
            <p className="muted small">Theo dõi trạng thái xử lý các hồ sơ đã gửi.</p>
          </div>
          <span className="badge badge-gray">{applications.length} hồ sơ</span>
        </div>
        {error && <div className="alert-box alert-error" role="alert">{error}</div>}
        {loading ? (
          <div className="empty-state" role="status">Đang tải danh sách hồ sơ…</div>
        ) : applications.length ? (
          <div className="application-table-wrap">
            <table className="application-table">
              <thead>
                <tr><th>Vị trí ứng tuyển</th><th>Doanh nghiệp</th><th>AI Match</th><th>Trạng thái</th><th>Ngày nộp</th><th aria-label="Thao tác" /></tr>
              </thead>
              <tbody>
                {applications.map((application) => (
                  <tr key={application.id}>
                    <td>{application.job_title || `Tin tuyển dụng ${application.job_id}`}</td>
                    <td className="muted">{application.company_name || '—'}</td>
                    <td><strong className="score-text">{application.ai_match_score == null ? '—' : `${application.ai_match_score}%`}</strong></td>
                    <td><span className={`status-badge ${statusTone[application.pipeline_status] || ''}`}>
                      {PIPELINE_STATUS_LABELS[application.pipeline_status] || application.pipeline_status}
                    </span></td>
                    <td className="muted">{application.applied_at ? new Date(application.applied_at).toLocaleDateString('vi-VN') : '—'}</td>
                    <td><Link className="inline-link" to={`/candidate/applications/${application.id}`}>Chi tiết</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <strong>Bạn chưa có đơn ứng tuyển</strong>
            <p>Hãy khám phá các vị trí đang tuyển dụng để bắt đầu.</p>
            <Link className="btn btn-primary" to="/candidate/jobs">Tìm việc làm</Link>
          </div>
        )}
      </section>
    </div>
  );
}
