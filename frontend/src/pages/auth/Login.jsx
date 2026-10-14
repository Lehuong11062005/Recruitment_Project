import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { ROLES } from '../../constants/roles';

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
    <div className="auth-wrapper">
      <div className="auth-card">
        <div className="auth-header">
          <span className="auth-brand">Smart Recruitment Platform</span>
          <h1 className="auth-title">Đăng nhập hệ thống</h1>
          <p className="auth-subtitle">
            Nhập thông tin tài khoản của bạn để tiếp tục làm việc.
          </p>
        </div>

        {registeredMessage && !serverError && (
          <div className="alert-box alert-success" role="status">
            {registeredMessage}
          </div>
        )}

        {serverError && (
          <div className="alert-box alert-error" role="alert">
            {serverError}
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate>
          <div className="form-group">
            <label htmlFor="login-email" className="form-label">
              Email <span className="form-required">*</span>
            </label>
            <input
              id="login-email"
              type="email"
              className={`form-input ${fieldErrors.email ? 'input-error' : ''}`}
              placeholder="name@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
            />
            {fieldErrors.email && (
              <p className="field-error">{fieldErrors.email}</p>
            )}
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
            />
            {fieldErrors.password && (
              <p className="field-error">{fieldErrors.password}</p>
            )}
          </div>

          <button type="submit" className="btn-primary" disabled={submitting}>
            {submitting ? 'Đang xác thực...' : 'Đăng nhập'}
          </button>
        </form>

        <div className="auth-footer">
          Chưa có tài khoản?{' '}
          <Link to="/register">Đăng ký tài khoản mới</Link>
        </div>
      </div>
    </div>
  );
};

export default Login;