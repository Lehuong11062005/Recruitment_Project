import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import Icon from '../../components/Icon';
import PdfPreviewer from '../../components/PdfPreviewer';
import { PIPELINE_STATUS, PIPELINE_STATUS_LABELS } from '../../constants/status';
import { applicationService } from '../../services/applicationService';
import { jobService } from '../../services/jobService';
import { useNavigate } from 'react-router-dom';
import { chatService } from '../../services/chatService';

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

// ================= đổi trạng thái hồ sơ, lịch phỏng vấn, ghi chú nội bộ =================
const toInputDateTime = (value) => (typeof value === 'string' ? value.slice(0, 16) : '');

const scheduleDraftFrom = (schedule) => ({
  time: toInputDateTime(schedule?.time),
  location: schedule?.location || '',
  link: schedule?.link || '',
});

const draftFromDetail = (detail) => ({
  status: detail?.pipeline_status || '',
  note: detail?.recruiter_note || '',
  ...scheduleDraftFrom(detail?.interview_schedule),
});

const totalExperienceYears = (experience) => (Array.isArray(experience) ? experience : [])
  .reduce((sum, item) => {
    const years = Number(item?.years);
    return Number.isFinite(years) && years > 0 ? sum + years : sum;
  }, 0);

const validateSchedule = (draft) => {
  if (!draft.time) return 'Vui lòng chọn ngày giờ phỏng vấn.';
  if (Number.isNaN(new Date(draft.time).getTime())) return 'Ngày giờ phỏng vấn không hợp lệ.';
  if (!draft.location.trim() && !draft.link.trim()) return 'Nhập địa điểm hoặc link phỏng vấn online.';
  return '';
};

// datetime-local trả "YYYY-MM-DDTHH:mm"; backend nhận ISO nên bổ sung giây.
const scheduleBody = (draft) => ({
  time: draft.time.length === 16 ? `${draft.time}:00` : draft.time,
  location: draft.location.trim(),
  link: draft.link.trim(),
});

/**
 * Dữ liệu + hành động cho phần HR duyệt hồ sơ đang chọn.
 * store[id] = { detail, error, draft }: nhớ theo id để chuyển qua lại không mất nội dung đang nhập.
 */
function useApplicationReview(activeId, onSaved) {
  const [store, setStore] = useState({});
  const [busy, setBusy] = useState('');
  const [feedback, setFeedback] = useState({ id: '', kind: '', type: '', text: '' });
  const [modalOpen, setModalOpen] = useState(false);
  const [modalError, setModalError] = useState('');

  const entry = activeId ? store[activeId] : undefined;
  const persistedStatus = entry?.detail?.pipeline_status || '';

  useEffect(() => {
    if (!activeId || store[activeId]) return undefined;
    let active = true;
    safely(() => applicationService.getApplicationDetail(activeId))
      .then((detail) => {
        if (active) setStore((prev) => ({ ...prev, [activeId]: { detail, error: '', draft: draftFromDetail(detail) } }));
      })
      .catch((error) => {
        if (active) {
          setStore((prev) => ({
            ...prev,
            [activeId]: { detail: null, draft: null, error: error?.message || 'Không thể tải chi tiết hồ sơ.' },
          }));
        }
      });
    return () => { active = false; };
  }, [activeId, store]);

  const reload = () => {
    setStore((prev) => {
      const next = { ...prev };
      delete next[activeId];
      return next;
    });
  };

  const patchDraft = (patch) => {
    setStore((prev) => {
      const current = prev[activeId];
      if (!current?.draft) return prev;
      return { ...prev, [activeId]: { ...current, draft: { ...current.draft, ...patch } } };
    });
  };

  const say = (id, kind, type, text) => setFeedback({ id, kind, type, text });

  const submit = async (kind, payload, successText) => {
    const id = activeId;
    if (!id || busy) return false;
    setBusy(kind);
    setFeedback({ id: '', kind: '', type: '', text: '' });
    try {
      const result = await applicationService.updateApplicationStatus(id, payload);
      setStore((prev) => {
        const current = prev[id];
        if (!current?.detail) return prev;
        const detail = {
          ...current.detail,
          pipeline_status: result.pipeline_status,
          recruiter_note: result.recruiter_note,
          interview_schedule: result.interview_schedule,
          status_history: result.status_history,
        };
        // Chỉ đồng bộ phần vừa lưu, giữ nguyên những ô HR đang nhập dở.
        const draftPatch = { status: result.pipeline_status };
        if ('recruiter_note' in payload) draftPatch.note = result.recruiter_note || '';
        if (payload.interview_schedule) Object.assign(draftPatch, scheduleDraftFrom(result.interview_schedule));
        return { ...prev, [id]: { ...current, detail, draft: { ...current.draft, ...draftPatch } } };
      });
      onSaved(id, result);
      say(id, kind, 'success', successText);
      return true;
    } catch (error) {
      say(id, kind, 'error', error?.message || 'Không thể cập nhật hồ sơ này.');
      return false;
    } finally {
      setBusy('');
    }
  };

  // Chọn trạng thái trong dropdown; chọn INTERVIEW thì mở modal nhập lịch phỏng vấn.
  const chooseStatus = (status) => {
    patchDraft({ status });
    setFeedback({ id: '', kind: '', type: '', text: '' });
    if (status === 'INTERVIEW' && persistedStatus !== 'INTERVIEW') {
      setModalError('');
      setModalOpen(true);
    }
  };

  const cancelModal = () => {
    setModalOpen(false);
    setModalError('');
    if (persistedStatus) patchDraft({ status: persistedStatus });
  };

  const confirmModal = () => {
    const problem = entry?.draft ? validateSchedule(entry.draft) : '';
    if (problem) {
      setModalError(problem);
      return;
    }
    setModalError('');
    setModalOpen(false);
  };

  const saveStatus = () => {
    const draft = entry?.draft;
    if (!draft || draft.status === persistedStatus) return false;
    if (draft.status === 'INTERVIEW') {
      if (validateSchedule(draft)) {
        setModalError('');
        setModalOpen(true);
        return false;
      }
      return submit('status', { pipeline_status: 'INTERVIEW', interview_schedule: scheduleBody(draft) }, 'Đã cập nhật trạng thái và gửi lịch phỏng vấn cho ứng viên.');
    }
    return submit('status', { pipeline_status: draft.status }, 'Đã cập nhật trạng thái hồ sơ và thông báo cho ứng viên.');
  };

  const sendSchedule = () => {
    const draft = entry?.draft;
    if (!draft) return false;
    const problem = validateSchedule(draft);
    if (problem) {
      say(activeId, 'schedule', 'error', problem);
      return false;
    }
    return submit('schedule', { pipeline_status: 'INTERVIEW', interview_schedule: scheduleBody(draft) }, 'Đã gửi lịch phỏng vấn cho ứng viên.');
  };

  const saveNote = () => {
    const draft = entry?.draft;
    if (!draft || !persistedStatus) return false;
    return submit('note', { pipeline_status: persistedStatus, recruiter_note: draft.note.trim() }, 'Đã lưu ghi chú nội bộ.');
  };

  return {
    entry,
    loading: Boolean(activeId) && !entry,
    persistedStatus,
    busy,
    feedback: feedback.id === activeId ? feedback : { id: '', kind: '', type: '', text: '' },
    modalOpen,
    modalError,
    reload,
    patchDraft,
    chooseStatus,
    cancelModal,
    confirmModal,
    saveStatus,
    sendSchedule,
    saveNote,
  };
}

function ReviewFeedback({ feedback, kinds }) {
  if (!feedback.text || !kinds.includes(feedback.kind)) return null;
  return (
    <div className={`alert-box ${feedback.type === 'success' ? 'alert-success' : 'alert-error'} crr-feedback`} role={feedback.type === 'success' ? 'status' : 'alert'}>
      {feedback.text}
    </div>
  );
}

function InterviewModal({ draft, error, onChange, onCancel, onConfirm }) {
  useEffect(() => {
    const onKeyDown = (event) => { if (event.key === 'Escape') onCancel(); };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onCancel]);

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onCancel(); }}>
      <div className="modal-card crr-modal" role="dialog" aria-modal="true" aria-labelledby="crr-modal-title">
        <h3 id="crr-modal-title">Lịch phỏng vấn</h3>
        <p className="muted small">Ứng viên sẽ nhận thông báo kèm lịch này khi bạn bấm “Lưu trạng thái”.</p>
        <label className="form-field">
          Ngày giờ
          <input className="input" type="datetime-local" autoFocus value={draft.time} onChange={(event) => onChange({ time: event.target.value })} />
        </label>
        <label className="form-field">
          Địa điểm
          <input className="input" placeholder="Phòng họp tầng 5 hoặc Phỏng vấn trực tuyến" value={draft.location} onChange={(event) => onChange({ location: event.target.value })} />
        </label>
        <label className="form-field">
          Link online
          <input className="input" inputMode="url" placeholder="https://meet.google.com/abc-defg-hij" value={draft.link} onChange={(event) => onChange({ link: event.target.value })} />
        </label>
        {error && <div className="alert-box alert-error" role="alert">{error}</div>}
        <div className="modal-actions">
          <button type="button" className="btn btn-secondary" onClick={onCancel}>Hủy</button>
          <button type="button" className="btn btn-primary" onClick={onConfirm}>Xác nhận lịch</button>
        </div>
      </div>
    </div>
  );
}

// Thẻ đầu cột phải: thông tin ứng viên, điểm AI và đổi pipeline_status.
function CandidateStatusCard({ selected, score, review }) {
  const { entry, loading, persistedStatus, busy, feedback } = review;
  const detail = entry?.detail || null;
  const draft = entry?.draft || null;
  const candidate = detail?.candidate || null;
  const years = totalExperienceYears(candidate?.experience);
  const position = (candidate?.experience || []).find((item) => item?.position)?.position;
  const subtitle = [
    position,
    candidate?.location,
    years > 0 ? `${Number(years.toFixed(1))} năm kinh nghiệm` : '',
  ].filter(Boolean).join(' · ');
  const contact = [selected.email, selected.phone].filter(Boolean).join(' · ');
  const dirty = Boolean(draft) && draft.status !== persistedStatus;

  // nút "Nhắn tin cho ứng viên" -> tạo/lấy hội thoại rồi mở màn hình Chat.
  const { jobId } = useParams();
  const navigate = useNavigate();
  const [chatBusy, setChatBusy] = useState(false);
  const [chatError, setChatError] = useState({ id: '', text: '' });
  const openChat = async () => {
    if (chatBusy) return;
    const candidateId = selected.candidate_id;
    if (!jobId || !candidateId) {
      setChatError({ id: String(selected.id), text: 'Thiếu thông tin tin tuyển dụng hoặc ứng viên để mở hội thoại.' });
      return;
    }
    setChatBusy(true);
    setChatError({ id: '', text: '' });
    try {
      const conversation = await chatService.createConversation({
        job_id: String(jobId),
        candidate_id: String(candidateId),
      });
      if (!conversation?.id) throw new Error('Không nhận được mã hội thoại từ máy chủ.');
      navigate(`/recruiter/messages/${encodeURIComponent(String(conversation.id))}`);
    } catch (error) {
      setChatError({ id: String(selected.id), text: error?.message || 'Không thể mở hội thoại với ứng viên này.' });
    } finally {
      setChatBusy(false);
    }
  };

  return (
    <section className="card crr-cand" aria-label="Thông tin ứng viên và trạng thái hồ sơ">
      <div className="crr-cand-info">
        <span className="avatar avatar-blue crr-cand-avatar" aria-hidden="true">{initials(selected.full_name)}</span>
        <div className="crr-cand-text">
          <h3>{selected.full_name || 'Ứng viên chưa có tên'}</h3>
          {loading && <span className="crr-skel crr-skel-line crr-cand-skel" aria-busy="true" />}
          {subtitle && <span>{subtitle}</span>}
          {contact && <span>{contact}</span>}
          <button type="button" className="btn btn-secondary crr-cand-chat" disabled={chatBusy} onClick={openChat}>
            <Icon name="message" size={16} /> {chatBusy ? 'Đang mở hội thoại...' : 'Nhắn tin cho ứng viên'}
          </button>
          {chatError.text && chatError.id === String(selected.id) && (
            <div className="alert-box alert-error crr-feedback" role="alert">{chatError.text}</div>
          )}
        </div>
      </div>

      <ScoreRing score={score} large />

      <div className="crr-cand-status">
        <label htmlFor="crr-pipeline-status">pipeline_status</label>
        <div className="crr-cand-controls">
          <select
            id="crr-pipeline-status"
            className="input"
            value={draft?.status || selected.pipeline_status || ''}
            disabled={!draft || Boolean(busy)}
            onChange={(event) => review.chooseStatus(event.target.value)}
          >
            {STATUS_ORDER.map((status) => <option key={status} value={status}>{status}</option>)}
          </select>
          <button type="button" className="btn btn-primary" disabled={!dirty || Boolean(busy)} onClick={review.saveStatus}>
            {busy === 'status' ? 'Đang lưu...' : 'Lưu trạng thái'}
          </button>
        </div>
        {draft?.status === 'INTERVIEW' && dirty && !validateSchedule(draft) && (
          <span className="crr-hint">Đã nhập lịch phỏng vấn. Bấm “Lưu trạng thái” để gửi cho ứng viên.</span>
        )}
        <ReviewFeedback feedback={feedback} kinds={['status']} />
      </div>

      {entry?.error && (
        <div className="crr-alert crr-cand-error" role="alert">
          <Icon name="warning" size={18} />
          <span><strong>Không tải được chi tiết hồ sơ</strong>{entry.error}</span>
          <button type="button" className="btn btn-secondary" onClick={review.reload}>Tải lại</button>
        </div>
      )}

      {review.modalOpen && draft && (
        <InterviewModal
          draft={draft}
          error={review.modalError}
          onChange={review.patchDraft}
          onCancel={review.cancelModal}
          onConfirm={review.confirmModal}
        />
      )}
    </section>
  );
}

// Thẻ cuối cột phải: lịch phỏng vấn (time, location, link) và recruiter_note.
function InterviewNoteCard({ review }) {
  const { entry, loading, busy, feedback } = review;
  const draft = entry?.draft || null;
  const noteDirty = Boolean(draft) && draft.note.trim() !== (entry?.detail?.recruiter_note || '').trim();

  return (
    <section className="card crr-schedule" aria-labelledby="crr-schedule-title">
      <h3 id="crr-schedule-title">Lịch phỏng vấn &amp; ghi chú nội bộ</h3>

      {loading && <div className="crr-skel crr-skel-block" aria-busy="true" />}

      {draft && (
        <>
          <div className="crr-schedule-grid">
            <label className="form-field">
              Ngày giờ
              <input className="input" type="datetime-local" value={draft.time} onChange={(event) => review.patchDraft({ time: event.target.value })} />
            </label>
            <label className="form-field">
              Địa điểm
              <input className="input" placeholder="Phỏng vấn trực tuyến" value={draft.location} onChange={(event) => review.patchDraft({ location: event.target.value })} />
            </label>
            <label className="form-field">
              Link online
              <input className="input" inputMode="url" placeholder="https://meet.google.com/abc-defg-hij" value={draft.link} onChange={(event) => review.patchDraft({ link: event.target.value })} />
            </label>
            <button type="button" className="btn btn-primary" disabled={Boolean(busy)} onClick={review.sendSchedule}>
              <Icon name="calendar" size={16} /> {busy === 'schedule' ? 'Đang gửi...' : 'Gửi lịch phỏng vấn'}
            </button>
          </div>
          <span className="crr-hint">Gửi lịch sẽ chuyển hồ sơ sang INTERVIEW và thông báo cho ứng viên.</span>
          <ReviewFeedback feedback={feedback} kinds={['schedule']} />

          <label className="form-field crr-note-field">
            recruiter_note
            <textarea
              className="input textarea"
              rows={4}
              maxLength={5000}
              placeholder="Ghi chú nội bộ, ứng viên không nhìn thấy."
              value={draft.note}
              onChange={(event) => review.patchDraft({ note: event.target.value })}
            />
          </label>
          <div>
            <button type="button" className="btn btn-secondary" disabled={!noteDirty || Boolean(busy)} onClick={review.saveNote}>
              {busy === 'note' ? 'Đang lưu...' : 'Lưu ghi chú nội bộ'}
            </button>
          </div>
          <ReviewFeedback feedback={feedback} kinds={['note']} />
        </>
      )}
    </section>
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

  //  đổi trạng thái, lịch phỏng vấn, ghi chú nội bộ của hồ sơ đang chọn.
  const review = useApplicationReview(activeId, (id, result) => {
    setCandidates((prev) => prev.map((item) => (String(item.id) === id
      ? { ...item, pipeline_status: result.pipeline_status }
      : item)));
  });

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
          {selected && <CandidateStatusCard selected={selected} score={score} review={review} />}
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
          {selected && <InterviewNoteCard review={review} />}
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
