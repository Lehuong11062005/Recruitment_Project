import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import Icon from '../../components/Icon';
import PdfPreviewer from '../../components/PdfPreviewer';
import { PIPELINE_STATUS, PIPELINE_STATUS_LABELS } from '../../constants/status';
import { applicationService } from '../../services/applicationService';
import { jobService } from '../../services/jobService';

const STATUS_ORDER = [
  PIPELINE_STATUS.APPLIED,
  PIPELINE_STATUS.SCREENING,
  PIPELINE_STATUS.INTERVIEW,
  PIPELINE_STATUS.HIRED,
  PIPELINE_STATUS.REJECTED,
];

const STATUS_BADGE = {
  [PIPELINE_STATUS.APPLIED]: 'badge-blue',
  [PIPELINE_STATUS.SCREENING]: 'badge-amber',
  [PIPELINE_STATUS.INTERVIEW]: 'badge-purple',
  [PIPELINE_STATUS.HIRED]: 'badge-green',
  [PIPELINE_STATUS.REJECTED]: 'badge-red',
};

// AI Service trả cả khóa *_match lẫn *_score; mỗi tiêu chí chỉ hiển thị một lần.
const BREAKDOWN_ROWS = [
  { label: 'Kỹ năng phù hợp', keys: ['skill_match', 'skill_score'] },
  { label: 'Kinh nghiệm phù hợp', keys: ['experience_match', 'experience_score'] },
  { label: 'Nội dung CV so với JD', keys: ['semantic_match', 'semantic_score'] },
];

const safely = (fn) => new Promise((resolve) => resolve(fn()));

const hasScore = (score) => score !== null && score !== undefined && !Number.isNaN(Number(score));

const clampPercent = (value) => Math.max(0, Math.min(100, Number(value) || 0));

const formatScore = (score) => (hasScore(score) ? `${Math.round(Number(score))}%` : '—');

const scoreLevel = (score) => {
  if (!hasScore(score)) return 'none';
  if (Number(score) >= 80) return 'high';
  if (Number(score) >= 50) return 'mid';
  return 'low';
};

const initials = (name = '') => name
  .split(/\s+/)
  .filter(Boolean)
  .slice(-2)
  .map((part) => part[0])
  .join('')
  .toUpperCase() || 'UV';

const formatDate = (value) => {
  if (!value) return '';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleDateString('vi-VN');
};

const getBreakdownRows = (breakdown) => {
  if (!breakdown || typeof breakdown !== 'object') return [];
  const known = new Set();
  const rows = [];

  BREAKDOWN_ROWS.forEach(({ label, keys }) => {
    keys.forEach((key) => known.add(key));
    const key = keys.find((candidate) => hasScore(breakdown[candidate]));
    if (key) rows.push({ key, label, value: clampPercent(breakdown[key]) });
  });

  Object.keys(breakdown).forEach((key) => {
    if (!known.has(key) && hasScore(breakdown[key])) {
      rows.push({ key, label: key, value: clampPercent(breakdown[key]) });
    }
  });

  return rows;
};

function ScoreRing({ score, large = false }) {
  const label = hasScore(score) ? `Điểm AI ${Math.round(Number(score))}%` : 'Chưa có điểm AI';
  return (
    <span className={`crr-ring ${scoreLevel(score)}${large ? ' lg' : ''}`} role="img" aria-label={label}>
      <span aria-hidden="true">{formatScore(score)}</span>
    </span>
  );
}

function SkillTags({ skills, tone, emptyText }) {
  if (!skills.length) return <p className="crr-none">{emptyText}</p>;
  return (
    <ul className="crr-tags">
      {skills.map((skill) => (
        <li key={String(skill.id || skill.name)} className={`crr-tag ${tone}`}>{skill.name}</li>
      ))}
    </ul>
  );
}

function RankingWorkspace({ jobId }) {
  const [jobTitle, setJobTitle] = useState('');
  const [candidates, setCandidates] = useState([]);
  const [loadState, setLoadState] = useState({ phase: 'loading', error: '' });
  const [reloadKey, setReloadKey] = useState(0);

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [minScore, setMinScore] = useState('');
  const [filterOpen, setFilterOpen] = useState(false);

  const [selectedId, setSelectedId] = useState('');
  const [details, setDetails] = useState({});
  const [retryingId, setRetryingId] = useState('');
  const [retryError, setRetryError] = useState({ id: '', message: '' });

  // Tên tin tuyển dụng (API riêng của recruiter, không có endpoint lấy 1 tin).
  useEffect(() => {
    let active = true;
    safely(() => jobService.getMyJobs())
      .then((response) => {
        const rows = Array.isArray(response?.data) ? response.data : [];
        const found = rows.find((job) => String(job.id || job._id) === String(jobId));
        if (active && found) setJobTitle(found.title || '');
      })
      .catch(() => {});
    return () => { active = false; };
  }, [jobId]);

  // Danh sách ứng viên đã xếp hạng.
  useEffect(() => {
    let active = true;
    safely(() => jobService.getJobApplications(jobId))
      .then((response) => {
        if (!active) return;
        setCandidates(Array.isArray(response) ? response : []);
        setLoadState({ phase: 'ready', error: '' });
      })
      .catch((error) => {
        if (!active) return;
        setLoadState({ phase: 'error', error: error?.message || 'Không thể tải danh sách ứng viên.' });
      });
    return () => { active = false; };
  }, [jobId, reloadKey]);

  const reload = () => {
    setLoadState({ phase: 'loading', error: '' });
    setReloadKey((key) => key + 1);
  };

  // Điểm cao → thấp, chưa có điểm xếp cuối;
  const ranked = useMemo(
    () => candidates
      .map((item) => ({ ...item, id: String(item.id) }))
      .sort((a, b) => (hasScore(b.ai_match_score) ? Number(b.ai_match_score) : -1)
        - (hasScore(a.ai_match_score) ? Number(a.ai_match_score) : -1))
      .map((item, index) => ({ ...item, rank: index + 1 })),
    [candidates],
  );

  const counts = useMemo(() => {
    const result = { ALL: ranked.length };
    STATUS_ORDER.forEach((status) => { result[status] = 0; });
    ranked.forEach((item) => {
      result[item.pipeline_status] = (result[item.pipeline_status] || 0) + 1;
    });
    return result;
  }, [ranked]);

  const visible = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    const minimum = minScore === '' ? null : clampPercent(minScore);
    return ranked.filter((item) => {
      if (statusFilter !== 'ALL' && item.pipeline_status !== statusFilter) return false;
      if (minimum !== null && (!hasScore(item.ai_match_score) || Number(item.ai_match_score) < minimum)) return false;
      if (keyword && !`${item.full_name} ${item.email}`.toLowerCase().includes(keyword)) return false;
      return true;
    });
  }, [ranked, search, statusFilter, minScore]);

  const selected = visible.find((item) => item.id === selectedId) || visible[0] || null;
  const activeId = selected ? selected.id : '';
  const filtersActive = statusFilter !== 'ALL' || minScore !== '' || search.trim() !== '';

  // Chi tiết phân tích AI của ứng viên đang chọn; lưu theo id để chuyển qua lại không gọi lại API.
  useEffect(() => {
    if (!activeId || details[activeId]) return undefined;
    let active = true;
    safely(() => applicationService.getAIAnalysis(activeId))
      .then((data) => {
        if (active) setDetails((prev) => ({ ...prev, [activeId]: { data, error: '' } }));
      })
      .catch((error) => {
        if (active) {
          setDetails((prev) => ({
            ...prev,
            [activeId]: { data: null, error: error?.message || 'Không thể tải phân tích AI.' },
          }));
        }
      });
    return () => { active = false; };
  }, [activeId, details]);

  const reloadDetail = (id) => {
    setDetails((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  };

  const handleRetry = async (id) => {
    setRetryingId(id);
    setRetryError({ id: '', message: '' });
    try {
      const data = await applicationService.retryAIAnalysis(id);
      setDetails((prev) => ({ ...prev, [id]: { data, error: '' } }));
      setCandidates((prev) => prev.map((item) => (String(item.id) === id
        ? {
          ...item,
          ai_match_score: data.ai_match_score,
          ai_status: data.ai_status,
          matched_skills: (data.ai_analysis?.matched || []).map(({ id: skillId, name }) => ({ id: skillId, name })),
          missing_skills: (data.ai_analysis?.missing || []).map(({ id: skillId, name }) => ({ id: skillId, name })),
        }
        : item)));
    } catch (error) {
      setRetryError({ id, message: error?.message || 'Không thể phân tích lại hồ sơ này.' });
    } finally {
      setRetryingId('');
    }
  };

  const resetFilters = () => {
    setSearch('');
    setStatusFilter('ALL');
    setMinScore('');
  };

  // ---- Dữ liệu cho thẻ Phân tích AI ----
  const entry = activeId ? details[activeId] : undefined;
  const detail = entry?.data || null;
  const analysis = detail?.ai_analysis || null;
  const aiStatus = detail?.ai_status || selected?.ai_status || '';
  const score = detail && hasScore(detail.ai_match_score) ? detail.ai_match_score : selected?.ai_match_score;
  const matchedSkills = analysis?.matched?.length ? analysis.matched : (selected?.matched_skills || []);
  const missingSkills = analysis?.missing?.length ? analysis.missing : (selected?.missing_skills || []);
  const breakdownRows = getBreakdownRows(analysis?.score_breakdown);
  const detailLoading = Boolean(activeId) && !entry;
  const isRetrying = retryingId === activeId && Boolean(activeId);
  const isProcessing = ['PENDING', 'PROCESSING'].includes(aiStatus);
  const noScore = !hasScore(score);

  if (loadState.phase === 'loading') {
    return (
      <div className="crr-page" aria-busy="true">
        <section className="card crr-head"><div><div className="crr-skel crr-skel-title" /><div className="crr-skel crr-skel-line" /></div></section>
        <div className="crr-split">
          <section className="card crr-list" aria-label="Đang tải danh sách ứng viên">
            {[0, 1, 2, 3].map((item) => (
              <div className="crr-row-skel" key={item}><span className="crr-skel crr-skel-avatar" /><span className="crr-skel crr-skel-line" /></div>
            ))}
          </section>
          <section className="card crr-ai"><div className="crr-ai-body"><div className="crr-skel crr-skel-title" /><div className="crr-skel crr-skel-block" /></div></section>
        </div>
      </div>
    );
  }

  if (loadState.phase === 'error') {
    return (
      <div className="crr-page">
        <section className="card">
          <div className="crr-alert" role="alert">
            <Icon name="warning" size={18} />
            <span><strong>Không tải được danh sách ứng viên</strong>{loadState.error}</span>
            <button type="button" className="btn btn-secondary" onClick={reload}>Thử lại</button>
          </div>
        </section>
      </div>
    );
  }

  if (ranked.length === 0) {
    return (
      <div className="crr-page">
        <section className="card empty-state">
          <Icon name="users" size={28} />
          <strong>Chưa có hồ sơ ứng tuyển</strong>
          <p>Khi ứng viên nộp hồ sơ vào tin này, danh sách sẽ được xếp hạng theo điểm AI tại đây.</p>
          <Link className="btn btn-secondary" to="/recruiter/jobs">Quay lại tin tuyển dụng</Link>
        </section>
      </div>
    );
  }

  return (
    <div className="crr-page">
      {/* ===== Thanh tiêu đề tin + bộ lọc trạng thái ===== */}
      <section className="card crr-head">
        <div>
          <h2>{jobTitle || 'Tin tuyển dụng'}</h2>
          <span className="crr-head-meta">{ranked.length} hồ sơ, sắp xếp giảm dần theo điểm AI</span>
        </div>
        <div className="crr-head-tools">
          <div className="crr-chips" role="group" aria-label="Lọc theo trạng thái hồ sơ">
            <button type="button" className="crr-chip" aria-pressed={statusFilter === 'ALL'} onClick={() => setStatusFilter('ALL')}>
              Tất cả <b>{counts.ALL}</b>
            </button>
            {STATUS_ORDER.map((status) => (
              <button key={status} type="button" className="crr-chip" aria-pressed={statusFilter === status} onClick={() => setStatusFilter(status)}>
                {PIPELINE_STATUS_LABELS[status]} <b>{counts[status] || 0}</b>
              </button>
            ))}
          </div>
          <button type="button" className="btn btn-secondary" aria-expanded={filterOpen} aria-controls="crr-filter-panel" onClick={() => setFilterOpen((open) => !open)}>
            <Icon name="filter" size={15} /> Bộ lọc
          </button>
        </div>
      </section>

      {filterOpen && (
        <section className="card crr-filter" id="crr-filter-panel">
          <label className="form-field">
            Điểm AI tối thiểu (0 – 100)
            <input
              className="input"
              type="number"
              inputMode="numeric"
              min="0"
              max="100"
              placeholder="Ví dụ: 70"
              value={minScore}
              onChange={(event) => setMinScore(event.target.value)}
            />
          </label>
          <button type="button" className="btn btn-ghost" onClick={resetFilters} disabled={!filtersActive}>Xóa bộ lọc</button>
        </section>
      )}

      <div className="crr-split">
        <section className="card crr-list" aria-labelledby="crr-list-title">
          <div className="crr-list-head">
            <div>
              <h3 id="crr-list-title">Xếp hạng ứng viên</h3>
              <span>Điểm AI, cao đến thấp</span>
            </div>
            <label className="mini-search">
              <Icon name="search" size={16} />
              <input
                aria-label="Tìm ứng viên theo tên hoặc email"
                placeholder="Tìm ứng viên"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </label>
          </div>

          {visible.length === 0 ? (
            <div className="empty-state crr-list-empty">
              <Icon name="search" size={24} />
              <strong>Không có ứng viên phù hợp</strong>
              <p>Thay đổi từ khóa hoặc bộ lọc để xem thêm hồ sơ.</p>
              <button type="button" className="btn btn-secondary" onClick={resetFilters}>Xóa bộ lọc</button>
            </div>
          ) : (
            <ul className="crr-rows">
              {visible.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    className="crr-row"
                    aria-current={item.id === activeId ? 'true' : undefined}
                    onClick={() => setSelectedId(item.id)}
                  >
                    <span className="crr-rank">#{item.rank}</span>
                    <span className="avatar avatar-blue" aria-hidden="true">{initials(item.full_name)}</span>
                    <span className="crr-row-main">
                      <strong>{item.full_name || 'Ứng viên chưa có tên'}</strong>
                      <span className="crr-sub">{item.email}{item.applied_at ? ` · Nộp ${formatDate(item.applied_at)}` : ''}</span>
                      <span className="crr-badges">
                        <span className={`badge ${STATUS_BADGE[item.pipeline_status] || 'badge-gray'}`}>
                          {PIPELINE_STATUS_LABELS[item.pipeline_status] || item.pipeline_status}
                        </span>
                        {item.ai_status === 'FAILED' && <span className="badge badge-red">AI lỗi</span>}
                      </span>
                    </span>
                    <ScoreRing score={item.ai_match_score} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <div className="crr-review">
          {!selected ? (
            <section className="card crr-ai">
              <div className="empty-state">
                <Icon name="spark" size={28} />
                <strong>Chọn một ứng viên</strong>
                <p>Phân tích AI của ứng viên sẽ hiển thị tại đây.</p>
              </div>
            </section>
          ) : (
            <section className="card crr-ai" aria-labelledby="crr-ai-title">
              <div className="crr-ai-head">
                <div className="crr-ident">
                  <span className="avatar avatar-blue" aria-hidden="true">{initials(selected.full_name)}</span>
                  <div>
                    <h3 id="crr-ai-title">Phân tích AI: {selected.full_name || 'Ứng viên'}</h3>
                    <span className="crr-ident-meta">
                      #{selected.rank} trong {ranked.length} hồ sơ
                      {detail?.matching_version ? ` · Phiên bản chấm điểm ${detail.matching_version}` : ''}
                    </span>
                  </div>
                </div>
                <ScoreRing score={score} large />
              </div>

              <div className="crr-ai-body">
                {isProcessing && (
                  <div className="crr-note" role="status">
                    <Icon name="clock" size={18} />
                    <span>AI đang phân tích CV của ứng viên này. Hãy tải lại sau ít phút.</span>
                  </div>
                )}

                {!isProcessing && noScore && (
                  <div className="crr-alert" role="alert">
                    <Icon name="warning" size={18} />
                    <span>
                      <strong>{aiStatus === 'FAILED' ? 'AI chưa phân tích được hồ sơ này' : 'Hồ sơ này chưa có điểm AI'}</strong>
                      {aiStatus === 'FAILED'
                        ? 'Bạn có thể yêu cầu AI phân tích lại CV.'
                        : 'Kết quả sẽ hiển thị khi AI chấm điểm xong.'}
                      {retryError.id === activeId && retryError.message ? ` ${retryError.message}` : ''}
                    </span>
                    {aiStatus === 'FAILED' && (
                      <button type="button" className="btn btn-primary" disabled={isRetrying} onClick={() => handleRetry(activeId)}>
                        {isRetrying ? 'Đang phân tích...' : 'Phân tích lại'}
                      </button>
                    )}
                  </div>
                )}

                {!isProcessing && !noScore && (
                  <>
                    <div>
                      <h4 className="crr-block-title">Điểm thành phần</h4>
                      {detailLoading && (
                        <div aria-busy="true" className="crr-breakdown">
                          <div className="crr-skel crr-skel-block" /><div className="crr-skel crr-skel-block" />
                        </div>
                      )}
                      {entry?.error && (
                        <div className="crr-alert" role="alert">
                          <Icon name="warning" size={18} />
                          <span><strong>Không tải được điểm thành phần</strong>{entry.error}</span>
                          <button type="button" className="btn btn-secondary" onClick={() => reloadDetail(activeId)}>Tải lại</button>
                        </div>
                      )}
                      {detail && breakdownRows.length === 0 && <p className="crr-none">AI chưa trả về điểm thành phần cho hồ sơ này.</p>}
                      {breakdownRows.length > 0 && (
                        <div className="crr-breakdown">
                          {breakdownRows.map((row) => (
                            <div className="crr-metric" key={row.key}>
                              <div className="crr-metric-top"><span>{row.label}</span><strong>{Math.round(row.value)}%</strong></div>
                              <div
                                className="bar"
                                role="progressbar"
                                aria-label={row.label}
                                aria-valuemin={0}
                                aria-valuemax={100}
                                aria-valuenow={Math.round(row.value)}
                              >
                                <i style={{ width: `${row.value}%` }} />
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="crr-skills">
                      <div>
                        <h4 className="crr-block-title">Kỹ năng trùng khớp ({matchedSkills.length})</h4>
                        <SkillTags skills={matchedSkills} tone="match" emptyText="Chưa có kỹ năng nào trùng với yêu cầu." />
                      </div>
                      <div>
                        <h4 className="crr-block-title">Kỹ năng còn thiếu ({missingSkills.length})</h4>
                        <SkillTags skills={missingSkills} tone="miss" emptyText="Ứng viên đáp ứng đủ kỹ năng bắt buộc." />
                      </div>
                    </div>

                    <div className="crr-advice">
                      <Icon name="spark" size={18} />
                      <div>
                        <strong>Lời khuyên từ AI</strong>
                        {detailLoading && <div className="crr-skel crr-skel-line" aria-busy="true" />}
                        {detail && <p>{analysis?.recommendation || 'AI chưa có lời khuyên cho hồ sơ này.'}</p>}
                        {entry?.error && <p>Chưa tải được lời khuyên.</p>}
                      </div>
                    </div>
                  </>
                )}
              </div>
            </section>
          )}
          {selected && <PdfPreviewer applicationId={activeId} fileName={`CV-${selected.full_name || activeId}.pdf`} />}
        </div>
      </div>
    </div>
  );
}

export default function CandidateRanking() {
  const { jobId } = useParams();
  // key={jobId}: đổi sang tin khác thì làm mới toàn bộ trạng thái màn hình.
  return <RankingWorkspace key={jobId} jobId={jobId} />;
}
