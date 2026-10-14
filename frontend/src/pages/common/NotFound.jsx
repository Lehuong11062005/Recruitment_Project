// File: frontend/src/pages/common/NotFound.jsx
import { Link } from 'react-router-dom';

export default function NotFound() {
  return (
    <div className="auth-wrapper">
      <div className="auth-card" style={{ textAlign: 'center' }}>
        <h1 className="auth-title">404 - Không tìm thấy trang</h1>
        <p className="auth-subtitle" style={{ marginBottom: '20px' }}>
          Đường dẫn bạn truy cập không tồn tại trên hệ thống.
        </p>
        <Link to="/">Quay về trang chính</Link>
      </div>
    </div>
  );
}