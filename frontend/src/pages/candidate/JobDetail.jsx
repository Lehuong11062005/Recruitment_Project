import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { API_URL, CANDIDATE_DEMO_MODE } from '../../config/env';
import { DEMO_JOBS } from '../../data/candidateDemo';
import { applicationService } from '../../services/applicationService';
import { aiMatchingService } from '../../services/aiMatchingService';
import { jobService } from '../../services/jobService';
import Icon from '../../components/Icon';

const MAX_CV_SIZE = 5 * 1024 * 1024;
const errorText = (error) => error?.message || 'Đã xảy ra lỗi, vui lòng thử lại.';

function normalizeJob(job, isDemo = false) {
  if (!job) return null;
  return {
    ...job,
    id: String(job.id ?? job._id ?? job.job_id ?? ''),
    title: job.title || 'Tin tuyển dụng chưa có tiêu đề',
    company_name: job.company_name || job.company?.name || job.company?.company_name || '',
    required_skills: Array.isArray(job.required_skill_names) && job.required_skill_names.length
      ? job.required_skill_names
      : job.required_skills,
    location: job.location || 'Chưa cập nhật địa điểm',
    isDemo: Boolean(job.isDemo || isDemo),
  };
}

function formatSalary(salary) {
  if (!salary) return 'Thỏa thuận';
  if (typeof salary === 'string') return salary;
  const format = (value) => new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 }).format(Number(value));
  const currency = salary.currency || 'VND';
  if (salary.min != null && salary.max != null) return `${format(salary.min)} – ${format(salary.max)} ${currency}`;
  if (salary.min != null) return `Từ ${format(salary.min)} ${currency}`;
  if (salary.max != null) return `Đến ${format(salary.max)} ${currency}`;
  return 'Thỏa thuận';
}

function validatePdf(file) {
  if (!file) return 'Vui lòng chọn CV PDF.';
  if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) return 'Chỉ chấp nhận tệp PDF.';
  if (file.size > MAX_CV_SIZE) return 'CV không được vượt quá 5 MB theo cấu hình Core Service hiện tại.';
  return '';
}

function displaySkill(skill) {
  if (typeof skill === 'string') return skill;
  return skill?.name || '';
}

export default function JobDetail() {
  const { jobId } = useParams();
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [apiUnavailable, setApiUnavailable] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [demoNotice, setDemoNotice] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [applyModalOpen, setApplyModalOpen] = useState(false);
  const [applyLoading, setApplyLoading] = useState(false);
  const [applyError, setApplyError] = useState('');
  const [applyMessage, setApplyMessage] = useState('');
  const [analysisFile, setAnalysisFile] = useState(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState('');
  const [analysisResult, setAnalysisResult] = useState(null);

  useEffect(() => {
    let active = true;
    Promise.resolve().then(async () => {
      if (!active) return;
      setLoading(true);
      setJob(null);
      setLoadError('');
      setDemoNotice('');
      setApiUnavailable(false);

      if (CANDIDATE_DEMO_MODE) {
        const sample = DEMO_JOBS.find((item) => String(item.id) === String(jobId));
        if (sample) {
          setJob(normalizeJob(sample, true));
          setApiUnavailable(false);
          setDemoNotice('DỮ LIỆU DEMO: các thao tác minh họa không gửi hoặc lưu dữ liệu lên backend.');
        } else {
          setLoadError('Không tìm thấy tin tuyển dụng trong bộ dữ liệu demo.');
        }
        setLoading(false);
        return;
      }
      if (!jobService.isDetailConfigured()) {
        setApiUnavailable(true);
        setLoading(false);
        return;
      }
      setApiUnavailable(false);

      try {
        const response = await jobService.getJobDetail(jobId);
        if (!active) return;
        const payload = response?.data ?? response;
        const rawJob = payload?.job ?? payload?.item ?? payload;
        const actualJob = normalizeJob(rawJob, false);
        if (!actualJob?.id) throw new Error('Response chi tiết Jobs không có ID hợp lệ.');
        if (rawJob.status && rawJob.status !== 'OPEN') throw new Error('Tin tuyển dụng này không còn mở.');
        if (rawJob.deleted_at) throw new Error('Tin tuyển dụng này đã bị xóa.');
        setJob(actualJob);
      } catch (error) {
        if (active) setLoadError(errorText(error));
      } finally {
        if (active) setLoading(false);
      }
    });
    return () => { active = false; };
  }, [jobId]);

  const changeFile = (event, purpose) => {
    const file = event.target.files?.[0] || null;
    const validation = file ? validatePdf(file) : '';
    if (purpose === 'apply') {
      setSelectedFile(validation ? null : file);
      setApplyError(validation);
      setApplyMessage('');
    } else {
      setAnalysisFile(validation ? null : file);
      setAnalysisError(validation);
      setAnalysisResult(null);
    }
  };

  const handleApply = async (event) => {
    event.preventDefault();
    setApplyError('');
    setApplyMessage('');
    const validation = validatePdf(selectedFile);
    if (validation) { setApplyError(validation); return; }
    if (!job) { setApplyError('Chưa có thông tin tin tuyển dụng.'); return; }

    if (CANDIDATE_DEMO_MODE) {
      setApplyMessage('Đã mô phỏng thao tác ứng tuyển. Không có đơn nào được tạo trên server.');
      setApplyModalOpen(false);
      return;
    }
    if (job.isDemo) {
      setApplyError('Không gửi đơn vì đây là tin tuyển dụng demo, không phải job đã lưu trong database. Hãy đợi API Jobs hoặc chọn một job ID thật.');
      return;
    }

    setApplyLoading(true);
    try {
      const response = await applicationService.applyJob(job.id, selectedFile);
      const pipelineStatus = response?.pipeline_status ? ` Trạng thái: ${response.pipeline_status}.` : '';
      const aiStatus = response?.ai_status ? ` AI: ${response.ai_status}.` : '';
      const score = response?.ai_match_score != null ? ` Điểm phù hợp: ${response.ai_match_score}%.` : '';
      setApplyMessage(`Backend đã nhận yêu cầu ứng tuyển thành công.${pipelineStatus}${aiStatus}${score}`);
      setApplyModalOpen(false);
      setSelectedFile(null);
    } catch (error) {
      setApplyError(errorText(error));
    } finally {
      setApplyLoading(false);
    }
  };

  const runAnalysis = async (event) => {
    event.preventDefault();
    setAnalysisError('');
    setAnalysisResult(null);
    const validation = validatePdf(analysisFile);
    if (validation) { setAnalysisError(validation); return; }
    if (!job) { setAnalysisError('Chưa có JD để so khớp.'); return; }

    if (CANDIDATE_DEMO_MODE) {
      setAnalysisResult({
        ai_match_score: 84,
        matching_version: 'DEMO',
        ai_analysis: { matched: [{ name: 'JavaScript' }, { name: 'HTML/CSS' }], missing: [{ name: 'Testing tự động' }], score_breakdown: { skills: 84 }, recommendation: 'Kết quả minh họa, không phải AI thật.' },
        demo: true,
      });
      return;
    }
    if (job.isDemo) {
      setAnalysisError('Không phân tích với AI thật vì JD này là dữ liệu mẫu. Cần API Jobs trả về JD từ database trước khi so khớp.');
      return;
    }

    setAnalysisLoading(true);
    try {
      const result = await aiMatchingService.previewJobCV(job.id, analysisFile);
      setAnalysisResult(result?.data ?? result);
    } catch (error) {
      setAnalysisError(errorText(error));
    } finally {
      setAnalysisLoading(false);
    }
  };

  if (loading) return <section className="card text-center text-slate-500">Đang tải chi tiết việc làm…</section>;
  if (apiUnavailable) return <div className="content-stack"><Link className="inline-link" to="/candidate/jobs">← Quay lại danh sách việc làm</Link><section role="status" className="api-unavailable"><h2>API Jobs chưa khả dụng</h2><p>Chi tiết việc làm cần API Jobs đang được bật và cấu hình. Không hiển thị tin demo thay cho tin thật.</p></section></div>;
  if (loadError || !job) return <div className="content-stack"><Link className="inline-link" to="/candidate/jobs">← Quay lại danh sách việc làm</Link><section role="alert" className="rounded-xl border border-amber-300 bg-amber-50 p-5 text-sm text-amber-900"><h2 className="text-lg font-bold">Chưa thể hiển thị chi tiết việc làm</h2><p className="mt-2">{loadError || 'Không tìm thấy tin tuyển dụng.'}</p></section></div>;

  const requiredSkills = (Array.isArray(job.required_skills) ? job.required_skills : []).map(displaySkill).filter(Boolean);
  const aiAnalysis = analysisResult?.ai_analysis || {};
  const resolvedCvUrl = job.cv_url ? (/^https?:\/\//i.test(job.cv_url) ? job.cv_url : `${API_URL.replace(/\/$/, '')}${job.cv_url}`) : '';

  return (
    <div className="content-stack">
      <Link to="/candidate/jobs" className="inline-link">← Quay lại danh sách việc làm</Link>
      {demoNotice && <div role="status" className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">{demoNotice}</div>}

      <section className="card">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0"><span className="badge badge-blue">UC-C5 · Chi tiết tin</span><h2 className="display-title">{job.title}</h2><p className="mt-1 font-semibold text-slate-600">{job.company_name || 'Nhà tuyển dụng chưa cập nhật'}</p><div className="mt-3 flex flex-wrap gap-2"><span className="badge badge-gray"><Icon name="map" size={13} />{job.location || 'Chưa cập nhật địa điểm'}</span>{job.level && <span className="badge badge-blue">{job.level}</span>}<span className="badge badge-green"><Icon name="wallet" size={13} />{formatSalary(job.salary)}</span></div></div>
          {job.isDemo && <span className="badge badge-amber">DỮ LIỆU DEMO</span>}
        </div>
        <div className="mt-6 border-t border-slate-100 pt-5"><h3 className="section-title">Mô tả công việc</h3><p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-700">{job.description || 'Chưa có mô tả công việc.'}</p></div>
        {requiredSkills.length > 0 && <div className="mt-5"><h3 className="section-title">Kỹ năng yêu cầu</h3><div className="mt-2 flex flex-wrap gap-2">{requiredSkills.map((skill) => <span key={skill} className="badge badge-gray">{skill}</span>)}</div></div>}
        {resolvedCvUrl && <p className="mt-3 text-sm"><a className="text-blue-700 underline" href={resolvedCvUrl} target="_blank" rel="noreferrer">Mở CV đính kèm</a></p>}
      </section>

      <div className="grid gap-5 lg:grid-cols-2">
        <section className="card">
          <div className="card-header"><div><span className="badge badge-blue">UC-C5</span><h3 className="section-title mt-2">Ứng tuyển vị trí này</h3><p className="muted small">Chọn CV PDF để gửi hồ sơ. Core Service giới hạn CV tối đa 5 MB.</p></div><span className="rounded-lg bg-blue-50 p-3 text-blue-700"><Icon name="upload" size={22} /></span></div>
          {applyMessage && <div className="alert-box alert-success mb-4" role="status">{applyMessage}</div>}
          <button type="button" onClick={() => { setApplyError(''); setApplyModalOpen(true); }} className="btn btn-primary full-button">
            <Icon name="send" size={15} />Ứng tuyển ngay
          </button>
          {job.isDemo && <p className="muted mt-3 text-xs">Không thể gửi đơn thật cho tin demo này.</p>}
        </section>

        <section className="card">
          <div className="card-header"><div><span className="badge badge-purple">UC-C6</span><h3 className="section-title mt-2">AI Matching</h3><p className="muted small">Tách nội dung CV PDF rồi so khớp với JD bằng AI Service.</p></div><span className="rounded-lg bg-violet-50 p-3 text-violet-700"><Icon name="spark" size={22} /></span></div>
          <form onSubmit={runAnalysis} className="space-y-4"><label className="block"><span className="mb-1 block text-sm font-semibold">CV để phân tích (PDF, tối đa 5 MB)</span><input type="file" accept=".pdf,application/pdf" onChange={(event) => changeFile(event, 'ai')} className="block w-full rounded-lg border border-slate-300 p-2 text-sm" />{analysisFile && <span className="muted mt-1 block text-xs">Đã chọn: {analysisFile.name}</span>}</label><button type="submit" disabled={analysisLoading} className="btn btn-secondary full-button disabled:opacity-50">{analysisLoading ? 'Đang phân tích…' : 'Phân tích độ phù hợp'}</button></form>
          {analysisError && <div role="alert" className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{analysisError}</div>}
          {analysisResult && <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
            {analysisResult.demo && <p className="mb-2 text-xs font-bold uppercase tracking-wide text-amber-700">Kết quả demo — không phải AI thật</p>}
            <div className="flex items-center gap-4"><div className="score-ring score-large"><span>{Math.round(Number(analysisResult.ai_match_score || 0))}%</span></div><div><p className="font-bold text-slate-900">Độ phù hợp CV – JD</p><p className="muted mt-1 text-xs">Phiên bản: {analysisResult.matching_version || 'Không có thông tin'}</p></div></div>
            {aiAnalysis.recommendation && <p className="mt-3 text-sm text-slate-700">{aiAnalysis.recommendation}</p>}
            {aiAnalysis.matched?.length > 0 && <div className="mt-3"><p className="text-sm font-semibold text-emerald-800">Kỹ năng phù hợp</p><div className="mt-1 flex flex-wrap gap-1">{aiAnalysis.matched.map((skill, index) => <span key={skill.id || skill.name || index} className="badge badge-green">{displaySkill(skill)}</span>)}</div></div>}
            {aiAnalysis.missing?.length > 0 && <div className="mt-3"><p className="text-sm font-semibold text-amber-800">Kỹ năng còn thiếu</p><div className="mt-1 flex flex-wrap gap-1">{aiAnalysis.missing.map((skill, index) => <span key={skill.id || skill.name || index} className="badge badge-amber">{displaySkill(skill)}</span>)}</div></div>}
            {aiAnalysis.score_breakdown && <details className="mt-3"><summary className="cursor-pointer text-sm font-semibold text-blue-700">Xem điểm chi tiết</summary><pre className="mt-2 overflow-auto rounded-lg bg-slate-900 p-3 text-xs text-white">{JSON.stringify(aiAnalysis.score_breakdown, null, 2)}</pre></details>}
          </div>}
        </section>
      </div>
      {applyModalOpen && (
        <div className="modal-backdrop" role="presentation" onMouseDown={(event) => {
          if (event.target === event.currentTarget && !applyLoading) setApplyModalOpen(false);
        }}>
          <section className="modal-card" role="dialog" aria-modal="true" aria-labelledby="apply-dialog-title">
            <div className="card-header">
              <div>
                <h2 className="section-title" id="apply-dialog-title">Ứng tuyển {job.title}</h2>
                <p className="muted small">Tải lên CV PDF, dung lượng tối đa 5 MB.</p>
              </div>
              <button type="button" className="btn btn-secondary" onClick={() => setApplyModalOpen(false)} disabled={applyLoading}>Đóng</button>
            </div>
            {applyError && <div className="alert-box alert-error mb-4" role="alert">{applyError}</div>}
            <form onSubmit={handleApply} className="space-y-4">
              <label className="block">
                <span className="mb-1 block text-sm font-semibold">CV ứng tuyển (PDF)</span>
                <input type="file" accept=".pdf,application/pdf" onChange={(event) => changeFile(event, 'apply')} className="block w-full rounded-lg border border-slate-300 p-2 text-sm" />
                {selectedFile && <span className="muted mt-1 block text-xs">Đã chọn: {selectedFile.name}</span>}
              </label>
              <button type="submit" disabled={applyLoading} className="btn btn-primary full-button">
                <Icon name="send" size={15} />{applyLoading ? 'Đang gửi…' : CANDIDATE_DEMO_MODE ? 'Mô phỏng ứng tuyển' : 'Gửi hồ sơ ứng tuyển'}
              </button>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}

export function LiveJobDetail() {
  const { jobId } = useParams();
  const [selectedFile, setSelectedFile] = useState(null);
  const [statusMsg, setStatusMsg] = useState('');
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    jobService.getJobDetail(jobId)
      .then((response) => {
        if (active) setJob(response?.data || response);
      })
      .catch((requestError) => {
        if (active) setError(requestError.message || 'Không thể tải thông tin tin tuyển dụng.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [jobId]);

  const handleApply = (event) => {
    event.preventDefault();
    setStatusMsg('Đã gửi yêu cầu ứng tuyển (UC-C5). Kết quả AI Matching sẽ được cập nhật.');
  };

  const salary = job?.salary
    ? `${Number(job.salary.min || 0).toLocaleString('vi-VN')} - ${Number(job.salary.max || 0).toLocaleString('vi-VN')} ${job.salary.currency || 'VND'}`
    : 'Thỏa thuận';

  return (
    <div className="content-stack">
      <Link to="/candidate/jobs" className="inline-link">
        <Icon name="chevron" size={16} className="back-chevron" /> Quay lại danh sách việc làm
      </Link>
      {error && <div className="alert-box alert-error" role="alert">{error}</div>}
      {loading && <section className="card empty-state">Đang tải thông tin tin tuyển dụng...</section>}
      {!loading && job && (
        <>
          <section className="card job-detail-hero">
            <div className="company-logo company-logo-large logo-blue">{(job.company_name || 'DN').slice(0, 2).toUpperCase()}</div>
            <div className="hero-job-copy">
              <span className="badge badge-blue">Tin tuyển dụng</span>
              <h2 className="display-title">{job.title}</h2>
              <span>{job.company_name || 'Doanh nghiệp'}</span>
            </div>
          </section>
          <div className="job-detail-grid">
            <section className="card">
              <div className="card-header">
                <div><h3 className="section-title">Thông tin tuyển dụng</h3><p className="muted small">Thông tin vị trí tuyển dụng được cung cấp bởi nhà tuyển dụng.</p></div>
              </div>
              <div className="meta-row">
                <span><Icon name="map" size={15} />{job.location || 'Chưa cập nhật'}</span>
                <span><Icon name="briefcase" size={15} />{job.level || 'MID'}</span>
                <span><Icon name="wallet" size={15} />{salary}</span>
                <span><Icon name="clock" size={15} />Kinh nghiệm: {job.experience_required || 0} năm</span>
              </div>
              <h3 className="section-title">Mô tả công việc</h3>
              <div className="job-description-content">{job.description}</div>
              <h3 className="section-title">Kỹ năng yêu cầu</h3>
              <p className="muted small">{Array.isArray(job.required_skill_names) && job.required_skill_names.length ? job.required_skill_names.join(', ') : 'Nhà tuyển dụng chưa chỉ định kỹ năng.'}</p>
            </section>
            <section className="card">
              <div className="card-header">
                <div><h3 className="section-title">Ứng tuyển vị trí này</h3><p className="muted small">Tải lên CV PDF để gửi hồ sơ ứng tuyển.</p></div>
              </div>
              {statusMsg && <div className="alert-box alert-success" role="status">{statusMsg}</div>}
              <form onSubmit={handleApply}>
                <div className="form-group">
                  <label htmlFor="live-application-cv" className="form-label">Chọn CV (PDF)</label>
                  <input id="live-application-cv" type="file" accept=".pdf,application/pdf" onChange={(event) => setSelectedFile(event.target.files?.[0] || null)} className="form-input" />
                  {selectedFile && <p className="field-hint">{selectedFile.name}</p>}
                  <p className="field-hint">Chỉ chấp nhận tệp PDF, tối đa 5 MB.</p>
                </div>
                <button type="submit" className="btn btn-primary full-button"><Icon name="send" size={16} /> Gửi hồ sơ ứng tuyển</button>
              </form>
            </section>
          </div>
        </>
      )}
      {!loading && !job && !error && <section className="card empty-state"><strong>Không tìm thấy tin tuyển dụng</strong><p>Tin này không còn mở hoặc đã được gỡ khỏi hệ thống.</p></section>}
    </div>
  );
}