// File: frontend/src/pages/common/NotFound.jsx
import { Link } from 'react-router-dom';

export default function NotFound() {
  return (
    <main className="error-page">
      <section className="card error-card">
        <span className="badge badge-gray">404</span>
        <h1>Không tìm thấy trang</h1>
        <p>
          Đường dẫn bạn truy cập không tồn tại trên hệ thống.
        </p>
        <Link to="/" className="btn btn-primary">Quay về trang chính</Link>
      </section>
    </main>
  );
}