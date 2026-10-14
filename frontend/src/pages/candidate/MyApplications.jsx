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

export default function MyApplications() {
  return (
    <div>
      <h1 style={{ fontSize: '22px', fontWeight: 700, color: '#142B4A', marginBottom: '16px' }}>
        Đơn ứng tuyển của tôi (UC-C7)
      </h1>

      <div
        style={{
          backgroundColor: '#FFFFFF',
          border: '1px solid #DCE5F0',
          borderRadius: '12px',
          overflow: 'hidden',
        }}
      >
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #DCE5F0', backgroundColor: '#F5F8FC' }}>
              <th style={{ padding: '14px 16px', fontSize: '13px', color: '#142B4A' }}>Vị trí ứng tuyển</th>
              <th style={{ padding: '14px 16px', fontSize: '13px', color: '#142B4A' }}>Doanh nghiệp</th>
              <th style={{ padding: '14px 16px', fontSize: '13px', color: '#142B4A' }}>Điểm AI Match</th>
              <th style={{ padding: '14px 16px', fontSize: '13px', color: '#142B4A' }}>Trạng thái (pipeline_status)</th>
              <th style={{ padding: '14px 16px', fontSize: '13px', color: '#142B4A' }}>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {MOCK_APPLICATIONS.map((app) => (
              <tr key={app.id} style={{ borderBottom: '1px solid #DCE5F0' }}>
                <td style={{ padding: '14px 16px', fontSize: '14px', fontWeight: 600 }}>
                  {app.job_title}
                </td>
                <td style={{ padding: '14px 16px', fontSize: '14px', color: '#64748B' }}>
                  {app.company_name}
                </td>
                <td style={{ padding: '14px 16px', fontSize: '14px', fontWeight: 700, color: '#155EEF' }}>
                  {app.ai_match_score}%
                </td>
                <td style={{ padding: '14px 16px', fontSize: '13px', fontWeight: 600 }}>
                  <span
                    style={{
                      padding: '4px 10px',
                      borderRadius: '8px',
                      border: '1px solid #DCE5F0',
                      backgroundColor: '#F5F8FC',
                      color: '#142B4A',
                    }}
                  >
                    {PIPELINE_STATUS_LABELS[app.pipeline_status] || app.pipeline_status}
                  </span>
                </td>
                <td style={{ padding: '14px 16px', fontSize: '14px' }}>
                  <Link to={`/candidate/applications/${app.id}`}>Xem chi tiết</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}