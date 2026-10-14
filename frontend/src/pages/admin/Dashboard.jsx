export default function Dashboard() {
  return (
    <div>
      <h1 style={{ fontSize: '22px', fontWeight: 700, color: '#142B4A', marginBottom: '12px' }}>
        Bảng điều khiển Quản trị viên (Admin Portal)
      </h1>
      <div
        style={{
          backgroundColor: '#FFFFFF',
          border: '1px solid #DCE5F0',
          borderRadius: '12px',
          padding: '24px',
        }}
      >
        <p style={{ fontSize: '14px', color: '#64748B' }}>
          Khung quản lý người dùng (UC-A1), kiểm duyệt doanh nghiệp (UC-A2), quản lý tin đăng (UC-A3) và thống kê hệ thống (UC-A4).
        </p>
      </div>
    </div>
  );
}