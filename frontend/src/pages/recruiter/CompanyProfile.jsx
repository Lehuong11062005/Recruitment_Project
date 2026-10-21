import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import Icon from '../../components/Icon';
import { useAuth } from '../../hooks/useAuth';
import api from '../../services/api';

const emptyCompany = {
  name: '',
  website: '',
  industry: '',
  address: '',
  description: '',
  logo_url: '',
};

const editableFields = Object.keys(emptyCompany);

export default function CompanyProfile() {
  const { user, updateUser } = useAuth();
  const [company, setCompany] = useState(null);
  const [form, setForm] = useState(emptyCompany);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  useEffect(() => {
    let active = true;

    if (!user?.company_id) {
      return () => {
        active = false;
      };
    }

    api.get(`/api/v1/companies/${user.company_id}`)
      .then((data) => {
        if (!active) return;
        setCompany(data);
        setForm(Object.fromEntries(editableFields.map((field) => [field, data?.[field] || ''])));
      })
      .catch((requestError) => {
        if (active) setError(requestError.message || 'Không thể tải hồ sơ doanh nghiệp.');
      });

    return () => {
      active = false;
    };
  }, [user?.company_id]);

  const completion = useMemo(() => {
    const completed = editableFields.filter((field) => form[field].trim()).length;
    return Math.round((completed / editableFields.length) * 100);
  }, [form]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setNotice('');

    try {
      const payload = Object.fromEntries(
        editableFields.map((field) => [field, form[field].trim() || null])
      );
      const companyId = company?.id || company?._id || user?.company_id;
      const updated = companyId
        ? await api.put(`/api/v1/companies/${companyId}`, payload)
        : await api.post('/api/v1/companies', payload);
      const savedCompanyId = updated?.id || updated?._id || companyId;
      if (!savedCompanyId) {
        throw new Error('Hệ thống chưa trả về mã doanh nghiệp sau khi lưu. Vui lòng tải lại trang và kiểm tra hồ sơ.');
      }

      setCompany(updated);
      if (!companyId) updateUser({ company_id: savedCompanyId });
      setForm(Object.fromEntries(editableFields.map((field) => [field, updated?.[field] || ''])));
      setNotice(companyId ? 'Đã lưu thay đổi. Hồ sơ chuyển về trạng thái PENDING để được duyệt lại.' : 'Đã tạo hồ sơ doanh nghiệp. Hồ sơ đang chờ quản trị viên duyệt.');
    } catch (requestError) {
      setError(requestError.message || 'Không thể lưu hồ sơ doanh nghiệp.');
    } finally {
      setSaving(false);
    }
  };

  const verificationStatus = company?.verification_status || 'PENDING';
  const isVerified = verificationStatus === 'VERIFIED';
  const isRejected = verificationStatus === 'REJECTED';
  const loading = Boolean(user?.company_id) && !company && !error;

  return (
    <div className="content-stack recruiter-workspace">
      <div className={`verification-banner ${isVerified ? 'verification-verified' : isRejected ? 'verification-rejected' : 'verification-pending'}`}>
        <span className="verification-icon"><Icon name={isVerified ? 'shield' : 'clock'} size={22} /></span>
        <div className="verification-copy">
          <div className="verification-heading">
            <strong>Trạng thái xác minh</strong>
            <span className={`status-badge ${isVerified ? 'success' : isRejected ? 'danger' : 'warning'}`}>{verificationStatus}</span>
          </div>
          <p>
            {isVerified
              ? 'Doanh nghiệp đã được xác minh. Tin tuyển dụng ở trạng thái OPEN có thể hiển thị công khai.'
              : isRejected
                ? 'Hồ sơ chưa đáp ứng yêu cầu. Hãy cập nhật thông tin và gửi lại để quản trị viên kiểm duyệt.'
                : 'Hồ sơ đang được quản trị viên kiểm duyệt. Bạn vẫn có thể tạo JD, nhưng tin tuyển dụng sẽ tạm ẩn với ứng viên cho tới khi doanh nghiệp được xác minh.'}
          </p>
        </div>
        <Link className="btn btn-secondary verification-action" to="/recruiter/jobs">
          <Icon name="briefcase" size={16} />
          Tin tuyển dụng
        </Link>
      </div>

      {error && <div className="alert-box alert-error" role="alert">{error}</div>}
      {notice && <div className="alert-box alert-success" role="status">{notice}</div>}

      {loading ? (
        <div className="card recruiter-loading" role="status">Đang tải hồ sơ doanh nghiệp…</div>
      ) : (
        <div className="company-profile-grid">
          <div className="content-stack">
            <section className="card recruiter-card">
              <div className="card-header">
                <div>
                  <h2 className="section-title">Thông tin doanh nghiệp</h2>
                  <p className="muted small">Thông tin hiển thị trên hồ sơ công ty và tin tuyển dụng.</p>
                </div>
              </div>
              <form className="recruiter-form" onSubmit={handleSubmit}>
                <label className="form-field">
                  <span>Tên công ty <b className="form-required">*</b></span>
                  <input className="input" name="name" value={form.name} onChange={handleChange} placeholder="VD: Công ty TNHH NovaTech Việt Nam" required />
                </label>
                <div className="form-grid two">
                  <label className="form-field">
                    <span>Website</span>
                    <input className="input" name="website" type="url" value={form.website} onChange={handleChange} placeholder="https://congty.vn" />
                  </label>
                  <label className="form-field">
                    <span>Ngành nghề</span>
                    <select className="input" name="industry" value={form.industry} onChange={handleChange}>
                      <option value="">Chọn ngành nghề</option>
                      <option>Công nghệ thông tin</option>
                      <option>Tài chính - Ngân hàng</option>
                      <option>Thương mại điện tử</option>
                      <option>Giáo dục</option>
                      <option>Khác</option>
                    </select>
                  </label>
                </div>
                <label className="form-field">
                  <span>Địa chỉ</span>
                  <input className="input" name="address" value={form.address} onChange={handleChange} placeholder="Quận/Huyện, Tỉnh/Thành phố" />
                </label>
                <label className="form-field">
                  <span>Logo công ty (URL)</span>
                  <input className="input" name="logo_url" type="url" value={form.logo_url} onChange={handleChange} placeholder="https://congty.vn/logo.png" />
                </label>
                <label className="form-field">
                  <span>Mô tả doanh nghiệp</span>
                  <textarea className="input textarea recruiter-description" name="description" rows={6} value={form.description} onChange={handleChange} placeholder="Giới thiệu lĩnh vực hoạt động, văn hóa và môi trường làm việc..." />
                </label>
                <div className="recruiter-form-actions">
                  <button className="btn btn-primary" type="submit" disabled={saving}>
                    <Icon name="check" size={16} />
                    {saving ? 'Đang lưu…' : company ? 'Lưu thay đổi' : 'Tạo hồ sơ doanh nghiệp'}
                  </button>
                  {company && <span className="muted small">Cập nhật hồ sơ sẽ gửi lại yêu cầu duyệt.</span>}
                </div>
              </form>
            </section>
            <section className="card recruiter-card recruiter-policy-card">
              <div className="card-header">
                <div>
                  <h2 className="section-title">Cơ chế duyệt mềm</h2>
                  <p className="muted small">Quy trình tuyển dụng vẫn tiếp tục trong thời gian xác minh doanh nghiệp.</p>
                </div>
              </div>
              <div className="policy-list">
                <div><i>1</i><span><strong>Tạo JD bất cứ lúc nào</strong>Nhà tuyển dụng có thể soạn và lưu tin trong khi hồ sơ đang chờ duyệt.</span></div>
                <div><i>2</i><span><strong>Tin tạm ẩn khi PENDING</strong>JD được chuyển sang HIDDEN để ứng viên chưa thể tìm thấy hoặc ứng tuyển.</span></div>
                <div><i>3</i><span><strong>Công khai sau khi VERIFIED</strong>Nhà tuyển dụng có thể mở lại các tin sau khi doanh nghiệp được xác minh.</span></div>
              </div>
            </section>
          </div>

          <aside className="content-stack">
            <section className="card recruiter-card">
              <div className="card-header">
                <div>
                  <h2 className="section-title">Độ hoàn thiện hồ sơ</h2>
                  <p className="muted small">Bổ sung thông tin để ứng viên hiểu hơn về doanh nghiệp.</p>
                </div>
              </div>
              <div className="completion-summary"><strong>{completion}%</strong><span>đã hoàn thiện</span></div>
              <div className="bar large-bar"><i style={{ width: `${completion}%` }} /></div>
              <div className="checklist">
                {editableFields.map((field) => (
                  <div className={form[field].trim() ? 'done' : ''} key={field}>
                    <Icon name={form[field].trim() ? 'check' : 'clock'} size={15} />
                    {({
                      name: 'Tên doanh nghiệp',
                      website: 'Website',
                      industry: 'Ngành nghề',
                      address: 'Địa chỉ',
                      description: 'Mô tả doanh nghiệp',
                      logo_url: 'Logo công ty',
                    })[field]}
                  </div>
                ))}
              </div>
            </section>
            <section className="card recruiter-card company-contact-card">
              <span className="company-contact-icon"><Icon name="shield" size={20} /></span>
              <h2 className="section-title">Hồ sơ pháp lý</h2>
              <p className="muted small">Trạng thái kiểm duyệt và giấy tờ xác minh được quản trị viên xử lý theo hồ sơ doanh nghiệp.</p>
              <span className={`status-badge ${isVerified ? 'success' : isRejected ? 'danger' : 'warning'}`}>{verificationStatus}</span>
            </section>
          </aside>
        </div>
      )}
    </div>
  );
}
