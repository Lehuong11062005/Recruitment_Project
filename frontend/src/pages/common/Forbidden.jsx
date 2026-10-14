// File: frontend/src/pages/common/Forbidden.jsx
import { Link } from 'react-router-dom';

export default function Forbidden() {
  return (
    <div className="auth-wrapper">
      <div className="auth-card" style={{ textAlign: 'center' }}>
        <h1 className="auth-title">403 - Không có quyền truy cập</h1>
        <p className="auth-subtitle" style={{ marginBottom: '20px' }}>
          Tài khoản của bạn không được cấp quyền sử dụng chức năng này.
        </p>
        <Link to="/">Quay về trang chính</Link>
      </div>
    </div>
  );
}