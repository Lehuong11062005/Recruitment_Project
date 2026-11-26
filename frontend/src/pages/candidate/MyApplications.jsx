import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Icon from '../../components/Icon';
import PipelineProgress from '../../components/PipelineProgress';
import { PIPELINE_STATUS, PIPELINE_STATUS_LABELS } from '../../constants/status';
import { applicationService } from '../../services/applicationService';

const STATUS_BADGE = {
  [PIPELINE_STATUS.APPLIED]: 'badge-blue',
  [PIPELINE_STATUS.SCREENING]: 'badge-amber',
  [PIPELINE_STATUS.INTERVIEW]: 'badge-purple',
  [PIPELINE_STATUS.HIRED]: 'badge-green',
  [PIPELINE_STATUS.REJECTED]: 'badge-red',
};

function formatDateTime(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString('vi-VN', {
    hour: '2-digit',
    minute: '2-digit',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}

export default function MyApplications() {
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadList = () => {
    setLoading(true);
    setError('');
    applicationService
      .getMyApplications()
      .then((result) => {
        const rows = result?.items ?? result;
        if (!Array.isArray(rows)) throw new Error('Danh sách đơn ứng tuyển không đúng định dạng.');
        setApplications(rows);
      })
      .catch((requestError) => {
        setError(requestError.message || 'Không thể tải danh sách đơn ứng tuyển.');
      })
      .finally(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    let active = true;
    applicationService
      .getMyApplications()
      .then((result) => {
        if (!active) return;
        const rows = result?.items ?? result;
        if (!Array.isArray(rows)) throw new Error('Danh sách đơn ứng tuyển không đúng định dạng.');
        setApplications(rows);
      })
      .catch((requestError) => {
        if (active) setError(requestError.message || 'Không thể tải danh sách đơn ứng tuyển.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="content-stack">
      <section className="card">
        <div className="card-header">
          <div>
            <h2 className="section-title">Danh sách đơn ứng tuyển</h2>
            <p className="muted small">Theo dõi tiến trình sơ loại, lịch phỏng vấn và kết quả tuyển dụng.</p>
          </div>
          <span className="badge badge-gray">{applications.length} hồ sơ</span>
        </div>

        {error && (
          <div className="alert-box alert-error" role="alert">
            <span>{error}</span>{' '}
            <button type="button" className="btn btn-secondary" onClick={loadList}>
              Thử lại
            </button>
          </div>
        )}

        {loading ? (
          <div className="empty-state" role="status">
            Đang tải danh sách hồ sơ…
          </div>
        ) : applications.length ? (
          <div className="my-app-list">
            {applications.map((application) => {
              const jobTitle =
                application.job?.title || application.job_title || `Tin tuyển dụng #${application.job_id}`;
              const companyName =
                application.company?.name || application.company_name || 'Doanh nghiệp';
              const jobDeleted = Boolean(application.job?.is_deleted);
              const schedule = application.interview_schedule;

              return (
                <article key={String(application.id)} className="my-app-card">
                  <div className="my-app-top">
                    <div className="my-app-heading">
                      <div className="my-app-title-row">
                        <h3>{jobTitle}</h3>
                        <span className={`badge ${STATUS_BADGE[application.pipeline_status] || 'badge-gray'}`}>
                          {PIPELINE_STATUS_LABELS[application.pipeline_status] || application.pipeline_status}
                        </span>
                        {jobDeleted && <span className="badge badge-gray">Tin đã gỡ</span>}
                      </div>
                      <div className="my-app-meta">
                        <span>
                          <Icon name="building" size={14} /> {companyName}
                        </span>
                        {application.job?.location && (
                          <span>
                            <Icon name="map" size={14} /> {application.job.location}
                          </span>
                        )}
                        <span>
                          <Icon name="clock" size={14} /> Nộp ngày:{' '}
                          {application.applied_at
                            ? new Date(application.applied_at).toLocaleDateString('vi-VN')
                            : '—'}
                        </span>
                        <span>
                          Điểm AI:{' '}
                          <strong className="score-text">
                            {application.ai_match_score == null
                              ? '—'
                              : `${Math.round(Number(application.ai_match_score))}%`}
                          </strong>
                        </span>
                      </div>
                    </div>

                    <Link
                      className="btn btn-secondary"
                      to={`/candidate/applications/${encodeURIComponent(String(application.id))}`}
                    >
                      Xem chi tiết
                    </Link>
                  </div>

                  <PipelineProgress status={application.pipeline_status} compact />

                  {schedule && (schedule.time || schedule.location || schedule.link) && (
                    <div className="my-app-interview-strip">
                      <Icon name="calendar" size={15} />
                      <span>
                        <strong>Lịch phỏng vấn:</strong>{' '}
                        {schedule.time ? formatDateTime(schedule.time) : 'Chưa rõ giờ'}
                        {schedule.location ? ` · Địa điểm: ${schedule.location}` : ''}
                      </span>
                      {schedule.link && (
                        <a
                          href={schedule.link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-link"
                        >
                          Tham gia online
                        </a>
                      )}
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        ) : !error ? (
          <div className="empty-state">
            <Icon name="briefcase" size={28} />
            <strong>Bạn chưa có đơn ứng tuyển</strong>
            <p>Hãy khám phá các vị trí đang tuyển dụng để bắt đầu nộp hồ sơ.</p>
            <Link className="btn btn-primary" to="/candidate/jobs">
              Tìm việc làm
            </Link>
          </div>
        ) : null}
      </section>
    </div>
  );
}
