import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import Icon from '../../components/Icon';
import { jobService } from '../../services/jobService';

export default function JobDetail() {
  const { jobId } = useParams();
  const [selectedFile, setSelectedFile] = useState(null);
  const [statusMsg, setStatusMsg] = useState('');
  const [job, setJob] = useState(null);
  const [jobError, setJobError] = useState('');

  useEffect(() => {
    let active = true;
    jobService.getJobDetail(jobId)
      .then((response) => {
        if (active) setJob(response?.data || response);
      })
      .catch((requestError) => {
        if (active) setJobError(requestError.message || 'Không thể tải thông tin tin tuyển dụng.');
      });
    return () => {
      active = false;
    };
  }, [jobId]);

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
          <h2 className="display-title">{job?.title || 'Chi tiết việc làm'}</h2>
          <span>{job?.company_name || `Mã tin: ${jobId}`}</span>
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
          {jobError && <div className="alert-box alert-error" role="alert">{jobError}</div>}
          {job ? (
            <div className="content-stack compact">
              <div className="meta-row">
                <span><Icon name="map" size={15} />{job.location || 'Chưa cập nhật'}</span>
                <span><Icon name="briefcase" size={15} />{job.level || 'MID'}</span>
                <span><Icon name="wallet" size={15} />{job.salary
                  ? `${Number(job.salary.min || 0).toLocaleString('vi-VN')} - ${Number(job.salary.max || 0).toLocaleString('vi-VN')} ${job.salary.currency || 'VND'}`
                  : 'Thỏa thuận'}</span>
                <span><Icon name="clock" size={15} />Kinh nghiệm: {job.experience_required || 0} năm</span>
              </div>
              <h4 className="section-title">Mô tả công việc</h4>
              <div className="job-description-content">{job.description}</div>
              <h4 className="section-title">Kỹ năng yêu cầu</h4>
              <p className="muted small">{Array.isArray(job.required_skill_names) && job.required_skill_names.length ? job.required_skill_names.join(', ') : 'Nhà tuyển dụng chưa chỉ định kỹ năng.'}</p>
            </div>
          ) : !jobError && (
            <div className="empty-state">
              <Icon name="file" size={25} />
              <strong>Đang tải thông tin tuyển dụng</strong>
              <p>Vui lòng chờ trong giây lát.</p>
            </div>
          )}
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
