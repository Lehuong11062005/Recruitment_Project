// File: frontend/src/pages/common/Forbidden.jsx
import { Link } from 'react-router-dom';

export default function Forbidden() {
  return (
    <main className="error-page">
      <section className="card error-card">
        <span className="badge badge-red">403</span>
        <h1>Không có quyền truy cập</h1>
        <p>
          Tài khoản của bạn không được cấp quyền sử dụng chức năng này.
        </p>
        <Link to="/" className="btn btn-primary">Quay về trang chính</Link>
      </section>
    </main>
  );
}