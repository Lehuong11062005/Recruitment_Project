import { useAuth } from '../../hooks/useAuth';

export default function ManageJobs() {
  const { user } = useAuth();

  return (
    <div>
      <h1 style={{ fontSize: '22px', fontWeight: 700, color: '#142B4A', marginBottom: '8px' }}>
        Quản lý tuyển dụng (Recruiter Portal)
      </h1>
      {!user?.company_id && (
        <div className="alert-box alert-error" style={{ marginTop: '12px' }}>
          Tài khoản của bạn chưa liên kết hồ sơ doanh nghiệp (company_id = null). Vui lòng cập nhật Hồ sơ doanh nghiệp (UC-R2) trước khi đăng tin tuyển dụng.
        </div>
      )}
      <div
        style={{
          backgroundColor: '#FFFFFF',
          border: '1px solid #DCE5F0',
          borderRadius: '12px',
          padding: '24px',
          marginTop: '16px',
        }}
      >
        <p style={{ fontSize: '14px', color: '#64748B' }}>
          Khung quản lý tin tuyển dụng (UC-R3) và xếp hạng ứng viên theo điểm AI Matching (UC-R4).
        </p>
      </div>
    </div>
  );
}