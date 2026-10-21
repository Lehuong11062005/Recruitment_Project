import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import Icon from '../../components/Icon';
import { API_URL } from '../../config/env';
import { PIPELINE_STATUS_LABELS } from '../../constants/status';
import { applicationService } from '../../services/applicationService';

const errorText = (error) => error?.message || 'Không thể tải thông tin hồ sơ.';

function cvHref(cvUrl) {
  if (!cvUrl) return '';
  return /^https?:\/\//i.test(cvUrl)
    ? cvUrl
    : `${API_URL.replace(/\/$/, '')}${cvUrl.startsWith('/') ? '' : '/'}${cvUrl}`;
}

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

  const analysis = application.ai_analysis || {};
  const cvUrl = cvHref(application.cv_url);

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
            {cvUrl && <a className="inline-link" href={cvUrl} target="_blank" rel="noreferrer">Mở CV đã nộp</a>}
            {application.parsed_text_preview && <p className="mt-3 whitespace-pre-wrap text-sm">{application.parsed_text_preview}</p>}
          </section>
        </div>
        <aside className="card analysis-detail">
          <div className="card-header">
            <div>
              <h3 className="section-title">Phân tích AI</h3>
              <p className="muted small">Kết quả phù hợp của hồ sơ ứng tuyển.</p>
            </div>
          </div>
          <div className="score-text text-2xl font-bold">
            {application.ai_match_score == null ? 'Chưa có điểm' : `${application.ai_match_score}%`}
          </div>
          <p className="muted small">Trạng thái AI: {application.ai_status}</p>
          {analysis.recommendation && <p className="mt-3 text-sm">{analysis.recommendation}</p>}
          {analysis.matched?.length > 0 && (
            <div className="mt-4">
              <strong>Kỹ năng khớp</strong>
              <div className="mt-2 flex flex-wrap gap-2">{analysis.matched.map((skill) => <span className="badge badge-green" key={skill.id}>{skill.name}</span>)}</div>
            </div>
          )}
          {analysis.missing?.length > 0 && (
            <div className="mt-4">
              <strong>Kỹ năng còn thiếu</strong>
              <div className="mt-2 flex flex-wrap gap-2">{analysis.missing.map((skill) => <span className="badge badge-amber" key={skill.id}>{skill.name}</span>)}</div>
            </div>
          )}
          <button type="button" className="btn btn-secondary full-button mt-5" onClick={retryAnalysis} disabled={retrying}>
            {retrying ? 'Đang phân tích lại…' : 'Phân tích lại'}
          </button>
        </aside>
      </div>
    </div>
  );
}
