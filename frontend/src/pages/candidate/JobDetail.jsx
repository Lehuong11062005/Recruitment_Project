import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import Icon from '../../components/Icon';

export default function JobDetail() {
  const { jobId } = useParams();
  const [selectedFile, setSelectedFile] = useState(null);
  const [statusMsg, setStatusMsg] = useState('');

  const handleApply = (event) => {
    event.preventDefault();
    setStatusMsg('Đã gửi yêu cầu ứng tuyển (UC-C5). Kết quả AI Matching sẽ được cập nhật.');
  };

  return (
    <div className="content-stack">
      <Link to="/candidate/jobs" className="inline-link">
        <Icon name="chevron" size={16} className="back-chevron" /> Quay lại danh sách việc làm
      </Link>
      <section className="card job-detail-hero">
        <div className="company-logo company-logo-large logo-blue"><Icon name="briefcase" /></div>
        <div className="hero-job-copy">
          <span className="badge badge-blue">Tin tuyển dụng</span>
          <h2 className="display-title">Chi tiết việc làm</h2>
          <span>Mã tin: {jobId}</span>
        </div>
      </section>

      <div className="job-detail-grid">
        <section className="card">
          <div className="card-header">
            <div>
              <h3 className="section-title">Thông tin tuyển dụng</h3>
              <p className="muted small">Thông tin vị trí tuyển dụng được cung cấp bởi nhà tuyển dụng.</p>
            </div>
          </div>
          <div className="empty-state">
            <Icon name="file" size={25} />
            <strong>Thông tin chi tiết chưa khả dụng</strong>
            <p>Không thể hiển thị mô tả công việc cho tin #{jobId} ở phiên bản hiện tại.</p>
          </div>
        </section>

        <section className="card">
          <div className="card-header">
            <div>
              <h3 className="section-title">Ứng tuyển vị trí này</h3>
              <p className="muted small">Tải lên CV PDF để gửi hồ sơ ứng tuyển.</p>
            </div>
          </div>
          {statusMsg && <div className="alert-box alert-success" role="status">{statusMsg}</div>}
          <form onSubmit={handleApply}>
            <div className="form-group">
              <label htmlFor="application-cv" className="form-label">Chọn CV (PDF)</label>
              <input
                id="application-cv"
                type="file"
                accept=".pdf,application/pdf"
                onChange={(event) => setSelectedFile(event.target.files?.[0] || null)}
                className="form-input"
              />
              {selectedFile && <p className="field-hint">{selectedFile.name}</p>}
              <p className="field-hint">Chỉ chấp nhận tệp PDF, tối đa 5 MB.</p>
            </div>
            <button type="submit" className="btn btn-primary full-button">
              <Icon name="send" size={16} /> Gửi hồ sơ ứng tuyển
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}
