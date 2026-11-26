import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import Icon from '../../components/Icon';
import MatchResultBox from '../../components/MatchResultBox';
import PdfPreviewer from '../../components/PdfPreviewer';
import PipelineProgress from '../../components/PipelineProgress';
import { PIPELINE_STATUS, PIPELINE_STATUS_LABELS } from '../../constants/status';
import { applicationService } from '../../services/applicationService';
import { chatService } from '../../services/chatService';

const STATUS_BADGE = {
  [PIPELINE_STATUS.APPLIED]: 'badge-blue',
  [PIPELINE_STATUS.SCREENING]: 'badge-amber',
  [PIPELINE_STATUS.INTERVIEW]: 'badge-purple',
  [PIPELINE_STATUS.HIRED]: 'badge-green',
  [PIPELINE_STATUS.REJECTED]: 'badge-red',
};

const errorText = (error) => error?.message || 'Không thể tải thông tin hồ sơ.';

function formatDateTime(value) {
  if (!value) return '—';
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

function ApplicationDetailView({ applicationId }) {
  const navigate = useNavigate();
  const [application, setApplication] = useState(null);
  const [loading, setLoading] = useState(true);
  const [retrying, setRetrying] = useState(false);
  const [chatBusy, setChatBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const loadApplication = useCallback(async () => {
    const result = await applicationService.getApplicationDetail(applicationId);
    setApplication(result?.data ?? result);
  }, [applicationId]);

  useEffect(() => {
    let active = true;
    applicationService
      .getApplicationDetail(applicationId)
      .then((result) => {
        if (active) setApplication(result?.data ?? result);
      })
      .catch((requestError) => {
        if (active) setError(errorText(requestError));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [applicationId]);

  const retryAnalysis = async () => {
    setRetrying(true);
    setError('');
    setNotice('');
    try {
      await applicationService.retryAIAnalysis(applicationId);
      await loadApplication();
      setNotice('Đã phân tích lại CV thành công.');
    } catch (requestError) {
      setError(errorText(requestError));
    } finally {
      setRetrying(false);
    }
  };

  const handleOpenChat = async () => {
    if (!application?.job_id || chatBusy) return;
    setChatBusy(true);
    setError('');
    try {
      const conv = await chatService.createConversation({
        job_id: String(application.job_id),
      });
      if (conv?.id) {
        navigate(`/candidate/chat/${encodeURIComponent(String(conv.id))}`);
      }
    } catch (err) {
      setError(err?.message || 'Không thể mở cuộc hội thoại cho vị trí này.');
    } finally {
      setChatBusy(false);
    }
  };

  if (loading) {
    return (
      <section className="card empty-state" role="status">
        Đang tải thông tin hồ sơ…
      </section>
    );
  }

  if (!application) {
    return (
      <div className="content-stack">
        <Link to="/candidate/applications" className="inline-link">
          <Icon name="chevron" size={16} className="back-chevron" /> Quay lại đơn ứng tuyển
        </Link>
        {error && (
          <section className="card alert-box alert-error" role="alert">
            {error}
          </section>
        )}
      </div>
    );
  }

  const jobTitle = application.job?.title || application.job_title || 'Chi tiết đơn ứng tuyển';
  const companyName = application.company?.name || application.company_name || 'Doanh nghiệp';
  const jobDeleted = Boolean(application.job?.is_deleted);
  const companyDeleted = Boolean(application.company?.is_deleted);
  const schedule = application.interview_schedule;
  const history = Array.isArray(application.status_history) ? application.status_history : [];

  return (
    <div className="content-stack">
      <Link to="/candidate/applications" className="inline-link">
        <Icon name="chevron" size={16} className="back-chevron" /> Quay lại đơn ứng tuyển
      </Link>

      {error && (
        <div className="alert-box alert-error" role="alert">
          {error}
        </div>
      )}
      {notice && (
        <div className="alert-box alert-success" role="status">
          {notice}
        </div>
      )}

      {/* Header thông tin công việc & doanh nghiệp */}
      <section className="card application-detail-head app-detail-hero">
        <div className="company-logo company-logo-large logo-blue">
          {companyName.slice(0, 2).toUpperCase()}
        </div>
        <div className="app-detail-hero-body">
          <div className="app-detail-badges">
            <span className={`badge ${STATUS_BADGE[application.pipeline_status] || 'badge-gray'}`}>
              {PIPELINE_STATUS_LABELS[application.pipeline_status] || application.pipeline_status}
            </span>
            {jobDeleted && <span className="badge badge-gray">Tin tuyển dụng đã ngừng hiển thị</span>}
            {companyDeleted && <span className="badge badge-gray">Doanh nghiệp không còn hoạt động</span>}
          </div>
          <h2 className="display-title">{jobTitle}</h2>
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
              <Icon name="clock" size={14} /> Nộp lúc: {formatDateTime(application.applied_at)}
            </span>
          </div>
        </div>
        {!jobDeleted && (
          <div className="button-row">
            <button
              type="button"
              className="btn btn-secondary"
              disabled={chatBusy}
              onClick={handleOpenChat}
            >
              <Icon name="message" size={16} />
              {chatBusy ? 'Đang mở...' : 'Nhắn tin HR'}
            </button>
            {application.job?.status === 'OPEN' && (
              <Link className="btn btn-secondary" to={`/candidate/jobs/${application.job_id}`}>
                Xem tin đăng
              </Link>
            )}
          </div>
        )}
      </section>

      {/* Thanh tiến trình 4 bước */}
      <section className="card" aria-labelledby="pipeline-progress-title">
        <div className="card-header">
          <div>
            <h3 className="section-title" id="pipeline-progress-title">
              Tiến trình ứng tuyển
            </h3>
            <p className="muted small">
              Trạng thái hiện tại:{' '}
              <strong>
                {PIPELINE_STATUS_LABELS[application.pipeline_status] || application.pipeline_status}
              </strong>
            </p>
          </div>
        </div>
        <PipelineProgress status={application.pipeline_status} />
      </section>

      {/* Lịch phỏng vấn (nếu có) */}
      {schedule && (schedule.time || schedule.location || schedule.link) && (
        <section className="card interview-detail-card" aria-labelledby="interview-card-title">
          <div className="card-header">
            <div>
              <span className="badge badge-purple">
                <Icon name="calendar" size={13} /> Lịch phỏng vấn
              </span>
              <h3 className="section-title mt-2" id="interview-card-title">
                Thông tin buổi phỏng vấn từ nhà tuyển dụng
              </h3>
            </div>
          </div>
          <div className="interview-detail-grid">
            <div>
              <span className="muted small">Thời gian</span>
              <strong>{formatDateTime(schedule.time)}</strong>
            </div>
            <div>
              <span className="muted small">Địa điểm / Hình thức</span>
              <strong>{schedule.location || 'Phỏng vấn trực tuyến'}</strong>
            </div>
            <div>
              <span className="muted small">Đường dẫn tham gia</span>
              {schedule.link ? (
                <a
                  href={schedule.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-link"
                >
                  {schedule.link}
                </a>
              ) : (
                <strong>Trực tiếp tại địa điểm</strong>
              )}
            </div>
          </div>
        </section>
      )}

      {/* Lịch sử thay đổi trạng thái */}
      <section className="card" aria-labelledby="status-history-title">
        <div className="card-header">
          <div>
            <h3 className="section-title" id="status-history-title">
              Lịch sử thay đổi trạng thái
            </h3>
            <p className="muted small">Ghi nhận các mốc cập nhật từ lúc nộp hồ sơ đến hiện tại.</p>
          </div>
        </div>
        {history.length === 0 ? (
          <p className="muted small">Chưa có bản ghi lịch sử trạng thái.</p>
        ) : (
          <ol className="status-history-list">
            {history.map((item, idx) => (
              <li key={`${item.status}-${item.time || idx}`} className="status-history-item">
                <span className={`badge ${STATUS_BADGE[item.status] || 'badge-gray'}`}>
                  {PIPELINE_STATUS_LABELS[item.status] || item.status}
                </span>
                <span className="status-history-time">{formatDateTime(item.time)}</span>
              </li>
            ))}
          </ol>
        )}
      </section>

      <div className="detail-layout">
        <div className="content-stack">
          <section className="card">
            <div className="card-header">
              <div>
                <h3 className="section-title">Tóm tắt nội dung CV</h3>
                <p className="muted small">Nội dung văn bản được trích xuất từ CV đã nộp.</p>
              </div>
            </div>
            {(application.cv_parsed_text || application.parsed_text_preview) ? (
              <p className="mt-2 whitespace-pre-wrap text-sm">
                {(application.cv_parsed_text || application.parsed_text_preview).slice(0, 600)}
              </p>
            ) : (
              <p className="muted small">Chưa có nội dung trích xuất văn bản.</p>
            )}
          </section>
          <PdfPreviewer applicationId={applicationId} />
        </div>

        <aside className="card analysis-detail">
          <div className="card-header">
            <div>
              <h3 className="section-title">Phân tích AI</h3>
              <p className="muted small">Độ phù hợp giữa CV đã nộp và yêu cầu công việc.</p>
            </div>
          </div>
          <MatchResultBox
            result={application}
            onRetry={retryAnalysis}
            retrying={retrying}
            retryDisabledReason={
              application.ai_status === 'FAILED'
                ? ''
                : 'Chỉ phân tích lại được khi AI báo lỗi (FAILED).'
            }
          />
        </aside>
      </div>
    </div>
  );
}


export default function ApplicationDetail() {
  const { applicationId } = useParams();
  return <ApplicationDetailView key={applicationId} applicationId={applicationId} />;
}
