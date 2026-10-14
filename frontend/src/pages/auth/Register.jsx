import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { ROLES } from '../../constants/roles';

const Register = () => {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    user_type: ROLES.CANDIDATE,
    full_name: '',
    email: '',
    phone: '',
    password: '',
    confirmPassword: '',
  });

  const [fieldErrors, setFieldErrors] = useState({});
  const [serverError, setServerError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (fieldErrors[field]) {
      setFieldErrors((prev) => ({ ...prev, [field]: '' }));
    }
  };

  const validateForm = () => {
    const errors = {};
    const trimmedName = formData.full_name.trim();
    const trimmedEmail = formData.email.trim();
    const trimmedPhone = formData.phone.trim();

    if (!trimmedName) {
      errors.full_name = 'Vui lòng nhập họ và tên.';
    } else if (trimmedName.length > 100) {
      errors.full_name = 'Họ và tên không được vượt quá 100 ký tự.';
    }

    if (!trimmedEmail) {
      errors.email = 'Vui lòng nhập địa chỉ email.';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      errors.email = 'Địa chỉ email không đúng định dạng.';
    }

    if (trimmedPhone && trimmedPhone.length > 20) {
      errors.phone = 'Số điện thoại không được vượt quá 20 ký tự.';
    }

    // Kiểm tra mật khẩu theo đúng quy tắc Backend của Cường: >= 8 ký tự và <= 72 byte
    const passwordByteLength = new TextEncoder().encode(formData.password).length;
    if (!formData.password || formData.password.length < 8) {
      errors.password = 'Mật khẩu phải có tối thiểu 8 ký tự.';
    } else if (passwordByteLength > 72) {
      errors.password = 'Mật khẩu vượt quá giới hạn 72 byte.';
    }

    if (formData.confirmPassword !== formData.password) {
      errors.confirmPassword = 'Mật khẩu xác nhận không khớp.';
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setServerError('');

    if (!validateForm()) return;

    setSubmitting(true);
    try {
      await register({
        email: formData.email,
        password: formData.password,
        full_name: formData.full_name,
        phone: formData.phone,
        user_type: formData.user_type,
      });

      navigate('/login', {
        replace: true,
        state: {
          email: formData.email.trim().toLowerCase(),
          registeredMessage: 'Đăng ký tài khoản thành công. Vui lòng đăng nhập để tiếp tục.',
        },
      });
    } catch (err) {
      setServerError(err?.message || 'Không thể đăng ký tài khoản. Vui lòng kiểm tra lại thông tin.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-wrapper">
      <div className="auth-card">
        <div className="auth-header">
          <span className="auth-brand">Smart Recruitment Platform</span>
          <h1 className="auth-title">Tạo tài khoản mới</h1>
          <p className="auth-subtitle">
            Chọn vai trò của bạn để thiết lập không gian làm việc phù hợp.
          </p>
        </div>

        <div className="role-selector" role="radiogroup" aria-label="Loại tài khoản">
          <button
            type="button"
            className={`role-option ${
              formData.user_type === ROLES.CANDIDATE ? 'active' : ''
            }`}
            onClick={() => handleChange('user_type', ROLES.CANDIDATE)}
          >
            <span className="role-option-title">Tôi là Ứng viên</span>
            <span className="role-option-desc">Tìm việc, tải CV & AI Matching</span>
          </button>

          <button
            type="button"
            className={`role-option ${
              formData.user_type === ROLES.RECRUITER ? 'active' : ''
            }`}
            onClick={() => handleChange('user_type', ROLES.RECRUITER)}
          >
            <span className="role-option-title">Nhà tuyển dụng</span>
            <span className="role-option-desc">Đăng tin JD & xếp hạng CV</span>
          </button>
        </div>

        {serverError && (
          <div className="alert-box alert-error" role="alert">
            {serverError}
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate>
          <div className="form-group">
            <label htmlFor="reg-fullname" className="form-label">
              {formData.user_type === ROLES.RECRUITER
                ? 'Họ và tên người đại diện'
                : 'Họ và tên'}{' '}
              <span className="form-required">*</span>
            </label>
            <input
              id="reg-fullname"
              type="text"
              className={`form-input ${fieldErrors.full_name ? 'input-error' : ''}`}
              placeholder="Nguyễn Văn A"
              value={formData.full_name}
              onChange={(e) => handleChange('full_name', e.target.value)}
              maxLength={100}
            />
            {fieldErrors.full_name && (
              <p className="field-error">{fieldErrors.full_name}</p>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="reg-email" className="form-label">
              Email đăng nhập <span className="form-required">*</span>
            </label>
            <input
              id="reg-email"
              type="email"
              className={`form-input ${fieldErrors.email ? 'input-error' : ''}`}
              placeholder="name@example.com"
              value={formData.email}
              onChange={(e) => handleChange('email', e.target.value)}
              autoComplete="email"
            />
            {fieldErrors.email && (
              <p className="field-error">{fieldErrors.email}</p>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="reg-phone" className="form-label">
              Số điện thoại liên hệ
            </label>
            <input
              id="reg-phone"
              type="tel"
              className={`form-input ${fieldErrors.phone ? 'input-error' : ''}`}
              placeholder="0901234567 (Không bắt buộc)"
              value={formData.phone}
              onChange={(e) => handleChange('phone', e.target.value)}
              maxLength={20}
            />
            {fieldErrors.phone && (
              <p className="field-error">{fieldErrors.phone}</p>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="reg-password" className="form-label">
              Mật khẩu <span className="form-required">*</span>
            </label>
            <input
              id="reg-password"
              type="password"
              className={`form-input ${fieldErrors.password ? 'input-error' : ''}`}
              placeholder="Tối thiểu 8 ký tự"
              value={formData.password}
              onChange={(e) => handleChange('password', e.target.value)}
              autoComplete="new-password"
            />
            {fieldErrors.password ? (
              <p className="field-error">{fieldErrors.password}</p>
            ) : (
              <p className="field-hint">Tối thiểu 8 ký tự, tối đa 72 byte.</p>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="reg-confirm-password" className="form-label">
              Xác nhận mật khẩu <span className="form-required">*</span>
            </label>
            <input
              id="reg-confirm-password"
              type="password"
              className={`form-input ${fieldErrors.confirmPassword ? 'input-error' : ''}`}
              placeholder="Nhập lại mật khẩu"
              value={formData.confirmPassword}
              onChange={(e) => handleChange('confirmPassword', e.target.value)}
              autoComplete="new-password"
            />
            {fieldErrors.confirmPassword && (
              <p className="field-error">{fieldErrors.confirmPassword}</p>
            )}
          </div>

          <button type="submit" className="btn-primary" disabled={submitting}>
            {submitting ? 'Đang khởi tạo tài khoản...' : 'Đăng ký tài khoản'}
          </button>
        </form>

        <div className="auth-footer">
          Đã có tài khoản?{' '}
          <Link to="/login">Đăng nhập ngay</Link>
        </div>
      </div>
    </div>
  );
};

export default Register;