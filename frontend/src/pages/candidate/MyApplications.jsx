import { Link } from 'react-router-dom';
import { PIPELINE_STATUS, PIPELINE_STATUS_LABELS } from '../../constants/status';

const MOCK_APPLICATIONS = [
  {
    id: 'app-001',
    job_title: 'Backend Developer (Python / FastAPI)',
    company_name: 'FPT Software',
    pipeline_status: PIPELINE_STATUS.APPLIED,
    ai_match_score: 86,
    applied_at: '15/10/2026',
  },
  {
    id: 'app-002',
    job_title: 'Frontend Engineer (ReactJS)',
    company_name: 'VNG Corporation',
    pipeline_status: PIPELINE_STATUS.INTERVIEW,
    ai_match_score: 92,
    applied_at: '12/10/2026',
  },
];

const statusTone = {
  [PIPELINE_STATUS.APPLIED]: '',
  [PIPELINE_STATUS.SCREENING]: 'warning',
  [PIPELINE_STATUS.INTERVIEW]: '',
  [PIPELINE_STATUS.HIRED]: 'success',
  [PIPELINE_STATUS.REJECTED]: 'danger',
};

export default function MyApplications() {
  return (
    <div className="content-stack">
      <section className="card">
        <div className="card-header">
          <div>
            <h2 className="section-title">Danh sách đơn ứng tuyển</h2>
            <p className="muted small">Theo dõi trạng thái xử lý các hồ sơ đã gửi.</p>
          </div>
          <span className="badge badge-gray">{MOCK_APPLICATIONS.length} hồ sơ</span>
        </div>
        {MOCK_APPLICATIONS.length > 0 ? (
          <div className="application-table-wrap">
            <div className="demo-disclaimer">
              <span>Danh sách hiện tại dùng các dữ liệu mẫu đã có trong frontend.</span>
            </div>
            <table className="application-table">
              <thead>
                <tr>
                  <th>Vị trí ứng tuyển</th>
                  <th>Doanh nghiệp</th>
                  <th>AI Match</th>
                  <th>Trạng thái</th>
                  <th>Ngày nộp</th>
                  <th aria-label="Thao tác" />
                </tr>
              </thead>
              <tbody>
                {MOCK_APPLICATIONS.map((application) => (
                  <tr key={application.id}>
                    <td>{application.job_title}</td>
                    <td className="muted">{application.company_name}</td>
                    <td><strong className="score-text">{application.ai_match_score}%</strong></td>
                    <td>
                      <span className={`status-badge ${statusTone[application.pipeline_status]}`}>
                        {PIPELINE_STATUS_LABELS[application.pipeline_status] || application.pipeline_status}
                      </span>
                    </td>
                    <td className="muted">{application.applied_at}</td>
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
