import { Link } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

export default function CandidateDashboard() {
  const { user } = useAuth();

  return (
    <div>
      <h1 style={{ fontSize: '24px', fontWeight: 700, color: '#142B4A', marginBottom: '6px' }}>
        Xin chào, {user?.full_name || 'Ứng viên'}
      </h1>
      <p style={{ fontSize: '14px', color: '#64748B', marginBottom: '24px' }}>
        Theo dõi các cơ hội nghề nghiệp và trạng thái hồ sơ ứng tuyển của bạn.
      </p>

      <div
        style={{
          backgroundColor: '#FFFFFF',
          border: '1px solid #DCE5F0',
          borderRadius: '12px',
          padding: '24px',
          marginBottom: '24px',
        }}
      >
        <h2 style={{ fontSize: '18px', fontWeight: 700, color: '#142B4A', marginBottom: '8px' }}>
          Việc làm phù hợp với bạn (AI Vector Recommendation)
        </h2>
        <p style={{ fontSize: '14px', color: '#64748B', marginBottom: '16px' }}>
          Hệ thống tự động đối chiếu kỹ năng trong hồ sơ của bạn với các tin tuyển dụng đang mở.
        </p>
        <Link
          to="/candidate/jobs"
          style={{
            display: 'inline-block',
            padding: '10px 16px',
            backgroundColor: '#155EEF',
            color: '#FFFFFF',
            borderRadius: '8px',
            fontSize: '14px',
            fontWeight: 600,
            textDecoration: 'none',
          }}
        >
          Khám phá danh sách việc làm
        </Link>
      </div>
    </div>
  );
}