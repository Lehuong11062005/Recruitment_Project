import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import Icon from '../../components/Icon';
import MatchResultBox from '../../components/MatchResultBox';
import PdfPreviewer from '../../components/PdfPreviewer';
import { PIPELINE_STATUS_LABELS } from '../../constants/status';
import { applicationService } from '../../services/applicationService';

const errorText = (error) => error?.message || 'Không thể tải thông tin hồ sơ.';

export default function ApplicationDetail() {
  const { applicationId } = useParams();
  const [application, setApplication] = useState(null);
  const [loading, setLoading] = useState(true);
  const [retrying, setRetrying] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const loadApplication = useCallback(async () => {
    const result = await applicationService.getAIAnalysis(applicationId);
    setApplication(result?.data ?? result);
  }, [applicationId]);

  useEffect(() => {
    let active = true;
    applicationService.getAIAnalysis(applicationId)
      .then((result) => {
        if (active) setApplication(result?.data ?? result);
      })
      .catch((requestError) => {
        if (active) setError(errorText(requestError));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [applicationId]);

  const retryAnalysis = async () => {
    setRetrying(true);
    setError('');
    setNotice('');
    try {
      const result = await applicationService.retryAIAnalysis(applicationId);
      setApplication(result?.data ?? result);
      setNotice('Đã phân tích lại CV thành công.');
      await loadApplication();
    } catch (requestError) {
      setError(errorText(requestError));
    } finally {
      setRetrying(false);
    }
  };

  if (loading) return <section className="card empty-state" role="status">Đang tải thông tin hồ sơ…</section>;
  if (!application) {
    return (
      <div className="content-stack">
        <Link to="/candidate/applications" className="inline-link">← Quay lại đơn ứng tuyển</Link>
        {error && <section className="card alert-box alert-error" role="alert">{error}</section>}
      </div>
    );
  }


  return (
    <div className="content-stack">
      <Link to="/candidate/applications" className="inline-link">
        <Icon name="chevron" size={16} className="back-chevron" /> Quay lại đơn ứng tuyển
      </Link>
      {error && <div className="alert-box alert-error" role="alert">{error}</div>}
      {notice && <div className="alert-box alert-success" role="status">{notice}</div>}
      <section className="card application-detail-head">
        <div className="company-logo company-logo-large logo-blue"><Icon name="file" /></div>
        <div>
          <span className="badge badge-gray">Đơn ứng tuyển</span>
          <h2 className="display-title">{application.job_title || 'Chi tiết hồ sơ'}</h2>
          <span className="muted small">{application.company_name || `Mã đơn: ${applicationId}`}</span>
          <p className="mt-2">
            Trạng thái: <strong>{PIPELINE_STATUS_LABELS[application.pipeline_status] || application.pipeline_status}</strong>
          </p>
        </div>
      </section>
      <div className="detail-layout">
        <div className="content-stack">
          <section className="card">
            <div className="card-header">
              <div>
                <h3 className="section-title">Thông tin hồ sơ</h3>
                <p className="muted small">CV và nội dung đã được gửi cùng đơn ứng tuyển.</p>
              </div>
            </div>
            {application.parsed_text_preview && <p className="mt-3 whitespace-pre-wrap text-sm">{application.parsed_text_preview}</p>}
          </section>
          <PdfPreviewer applicationId={applicationId} />
        </div>
        <aside className="card analysis-detail">
          <div className="card-header">
            <div>
              <h3 className="section-title">Phân tích AI</h3>
              <p className="muted small">Kết quả phù hợp của hồ sơ ứng tuyển.</p>
            </div>
          </div>
          <MatchResultBox
            result={application}
            onRetry={retryAnalysis}
            retrying={retrying}
            retryDisabledReason={application.ai_status === 'FAILED' ? '' : 'Chỉ phân tích lại được khi AI báo lỗi (FAILED).'}
          />
        </aside>
      </div>
    </div>
  );
}
