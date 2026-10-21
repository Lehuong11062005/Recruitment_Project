import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { ROLES } from '../../constants/roles';
import Icon from '../../components/Icon';

const Login = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const registeredMessage = location.state?.registeredMessage || '';
  const prefillEmail = location.state?.email || '';

  const [email, setEmail] = useState(prefillEmail);
  const [password, setPassword] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [serverError, setServerError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const validateForm = () => {
    const errors = {};
    const trimmedEmail = email.trim();

    if (!trimmedEmail) {
      errors.email = 'Vui lòng nhập địa chỉ email.';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      errors.email = 'Địa chỉ email không đúng định dạng.';
    }

    if (!password) {
      errors.password = 'Vui lòng nhập mật khẩu.';
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleRedirectByRole = (loggedInUser) => {
    if (loggedInUser.role === ROLES.ADMIN) {
      navigate('/admin', { replace: true });
      return;
    }

    if (loggedInUser.role === ROLES.RECRUITER || loggedInUser.user_type === ROLES.RECRUITER) {
      // Nếu Nhà tuyển dụng chưa có company_id, điều hướng kèm cờ nhắc tạo hồ sơ doanh nghiệp (UC-R2)
      if (!loggedInUser.company_id) {
        navigate('/recruiter/jobs', {
          replace: true,
          state: { requireCompanySetup: true },
        });
      } else {
        navigate('/recruiter/jobs', { replace: true });
      }
      return;
    }

    navigate('/candidate', { replace: true });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setServerError('');

    if (!validateForm()) return;

    setSubmitting(true);
    try {
      const loggedInUser = await login({ email, password });
      handleRedirectByRole(loggedInUser);
    } catch (err) {
      setServerError(err?.message || 'Email hoặc mật khẩu không đúng.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="auth-page">
      <section className="auth-brand">
        <Link to="/login" className="brand brand-light">
          <span className="brand-mark"><Icon name="spark" size={20} /></span><span>CareerAI</span>
        </Link>
        <div className="auth-copy">
          <span className="auth-kicker">NỀN TẢNG TUYỂN DỤNG THÔNG MINH</span>
          <h1 className="auth-title">Kết nối đúng người.<br />Kiến tạo đúng tương lai.</h1>
          <p>AI giúp ứng viên tìm đúng cơ hội và doanh nghiệp chọn đúng nhân tài — nhanh hơn, chính xác hơn.</p>
        </div>
        <div className="auth-features">
          <div><Icon name="file" /><span><strong>Hồ sơ nghề nghiệp tập trung</strong>Quản lý thông tin và CV tại một nơi</span></div>
          <div><Icon name="spark" /><span><strong>Cơ hội phù hợp</strong>Khám phá các vị trí tuyển dụng phù hợp</span></div>
          <div><Icon name="shield" /><span><strong>Tài khoản an toàn</strong>Đăng nhập bằng tài khoản đã đăng ký</span></div>
        </div>
      </section>
      <section className="auth-form-wrap">
        <div className="auth-form">
          <Link to="/login" className="brand mobile-brand">
            <span className="brand-mark"><Icon name="spark" size={20} /></span><span>CareerAI</span>
          </Link>
          <h2 className="auth-heading">Chào mừng bạn trở lại</h2>
          <p>Đăng nhập để tiếp tục hành trình nghề nghiệp.</p>
          <div className="auth-tabs" role="tablist" aria-label="Xác thực tài khoản">
            <button type="button" className="active" aria-selected="true">Đăng nhập</button>
            <Link to="/register">Đăng ký</Link>
          </div>

          {registeredMessage && !serverError && (
            <div className="alert-box alert-success" role="status">{registeredMessage}</div>
          )}
          {serverError && <div className="alert-box alert-error" role="alert">{serverError}</div>}

          <form onSubmit={handleSubmit} noValidate>
            <div className="form-group">
              <label htmlFor="login-email" className="form-label">
                Email <span className="form-required">*</span>
              </label>
              <input
                id="login-email"
                type="email"
                className={`form-input ${fieldErrors.email ? 'input-error' : ''}`}
                placeholder="name@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                aria-invalid={Boolean(fieldErrors.email)}
              />
              {fieldErrors.email && <p className="field-error">{fieldErrors.email}</p>}
            </div>

            <div className="form-group">
              <label htmlFor="login-password" className="form-label">
                Mật khẩu <span className="form-required">*</span>
              </label>
              <input
                id="login-password"
                type="password"
                className={`form-input ${fieldErrors.password ? 'input-error' : ''}`}
                placeholder="Nhập mật khẩu của bạn"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                aria-invalid={Boolean(fieldErrors.password)}
              />
              {fieldErrors.password && <p className="field-error">{fieldErrors.password}</p>}
            </div>

            <button type="submit" className="btn btn-primary full-button" disabled={submitting}>
              {submitting ? 'Đang xác thực...' : 'Đăng nhập'}
            </button>
          </form>
          <div className="auth-footer">
            Chưa có tài khoản? <Link to="/register">Đăng ký tài khoản mới</Link>
          </div>
        </div>
      </section>
    </main>
  );
};

export default Login;