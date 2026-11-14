import Icon from './Icon';

// AI Service trả cả khóa *_match lẫn *_score; mỗi tiêu chí chỉ hiển thị một lần.
const BREAKDOWN_ROWS = [
  { label: 'Kỹ năng phù hợp', keys: ['skill_match', 'skill_score'] },
  { label: 'Kinh nghiệm phù hợp', keys: ['experience_match', 'experience_score'] },
  { label: 'Nội dung CV so với JD', keys: ['semantic_match', 'semantic_score'] },
];

const hasScore = (v) => v !== null && v !== undefined && !Number.isNaN(Number(v));
const clamp = (v) => Math.max(0, Math.min(100, Number(v) || 0));
const skillName = (s) => (typeof s === 'string' ? s : s?.name || '');

function getBreakdownRows(breakdown) {
  if (!breakdown || typeof breakdown !== 'object') return [];
  const known = new Set();
  const rows = [];
  BREAKDOWN_ROWS.forEach(({ label, keys }) => {
    keys.forEach((k) => known.add(k));
    const key = keys.find((k) => hasScore(breakdown[k]));
    if (key) rows.push({ key, label, value: clamp(breakdown[key]) });
  });
  Object.keys(breakdown).forEach((key) => {
    if (!known.has(key) && hasScore(breakdown[key])) rows.push({ key, label: key, value: clamp(breakdown[key]) });
  });
  return rows;
}

function ScoreDonut({ score }) {
  const pct = clamp(score);
  const radius = 46;
  const circumference = 2 * Math.PI * radius;
  const color = pct >= 80 ? 'var(--green)' : pct >= 50 ? 'var(--amber)' : 'var(--color-error-text)';
  return (
    <div className="relative h-28 w-28 shrink-0" role="img" aria-label={`Điểm phù hợp ${Math.round(pct)}%`}>
      <svg viewBox="0 0 112 112" className="h-full w-full -rotate-90">
        <circle cx="56" cy="56" r={radius} fill="none" stroke="var(--border)" strokeWidth="10" />
        <circle
          cx="56" cy="56" r={radius} fill="none" stroke={color} strokeWidth="10" strokeLinecap="round"
          strokeDasharray={circumference} strokeDashoffset={circumference * (1 - pct / 100)}
          style={{ transition: 'stroke-dashoffset .6s ease' }}
        />
      </svg>
      <span className="absolute inset-0 grid place-items-center text-2xl font-bold" style={{ color }} aria-hidden="true">
        {Math.round(pct)}%
      </span>
    </div>
  );
}

function SkillTags({ title, skills, tone, emptyText }) {
  return (
    <div className="mt-4">
      <p className="text-sm font-semibold">{title} ({skills.length})</p>
      {skills.length === 0 ? (
        <p className="muted mt-1 text-xs">{emptyText}</p>
      ) : (
        <div className="mt-2 flex flex-wrap gap-2">
          {skills.map((skill, index) => (
            <span key={skill?.id || skillName(skill) || index} className={`badge ${tone}`}>{skillName(skill)}</span>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Box kết quả AI Matching (Task 7.2).
 * result: { ai_match_score, matching_version, ai_analysis: { matched_skills|matched, missing_skills|missing, score_breakdown, recommendation } }
 *   -> dùng được cho cả kết quả /ai-analysis/preview (JobDetail) và ApplicationResponse (ApplicationDetail).
 * onRetry: () => void; retryDisabledReason: nếu có chuỗi thì nút bị khóa và hiện lý do.
 */
export default function MatchResultBox({
  result,
  onRetry,
  retrying = false,
  retryDisabledReason = '',
  demo = false,
}) {
  if (!result) return null;
  const analysis = result.ai_analysis || {};
  const matched = analysis.matched_skills?.length ? analysis.matched_skills : analysis.matched || [];
  const missing = analysis.missing_skills?.length ? analysis.missing_skills : analysis.missing || [];
  const rows = getBreakdownRows(analysis.score_breakdown);
  const noScore = !hasScore(result.ai_match_score);

  return (
    <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
      {demo && <p className="mb-2 text-xs font-bold uppercase tracking-wide text-amber-700">Kết quả demo — không phải AI thật</p>}

      <div className="flex items-center gap-4">
        {noScore ? (
          <div className="grid h-28 w-28 shrink-0 place-items-center rounded-full border-8 border-slate-200 text-sm text-slate-500">Chưa có</div>
        ) : (
          <ScoreDonut score={result.ai_match_score} />
        )}
        <div className="min-w-0">
          <p className="font-bold text-slate-900">Độ phù hợp CV – JD</p>
          <p className="muted mt-1 text-xs">Phiên bản chấm điểm: {result.matching_version || 'Không có thông tin'}</p>
          {result.ai_status && <p className="muted mt-1 text-xs">Trạng thái AI: {result.ai_status}</p>}
        </div>
      </div>

      {rows.length > 0 && (
        <div className="mt-4 space-y-3">
          <p className="text-sm font-semibold">Điểm chi tiết</p>
          {rows.map((row) => (
            <div key={row.key}>
              <div className="flex justify-between text-xs"><span>{row.label}</span><strong>{Math.round(row.value)}%</strong></div>
              <div className="bar mt-1" role="progressbar" aria-label={row.label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(row.value)}>
                <i style={{ width: `${row.value}%` }} />
              </div>
            </div>
          ))}
        </div>
      )}

      <SkillTags title="Kỹ năng phù hợp" skills={matched} tone="badge-green" emptyText="Chưa có kỹ năng nào trùng với yêu cầu." />
      <SkillTags title="Kỹ năng còn thiếu" skills={missing} tone="badge-amber" emptyText="Đã đáp ứng đủ kỹ năng yêu cầu." />

      {analysis.recommendation && (
        <p className="mt-4 rounded-lg bg-white p-3 text-sm text-slate-700">
          <Icon name="spark" size={14} /> {analysis.recommendation}
        </p>
      )}

      {onRetry && (
        <div className="mt-4">
          <button type="button" className="btn btn-secondary full-button disabled:opacity-50" onClick={onRetry} disabled={retrying || Boolean(retryDisabledReason)}>
            {retrying ? 'Đang phân tích lại…' : 'Phân tích lại (Retry AI)'}
          </button>
          {retryDisabledReason && <p className="muted mt-1 text-xs">{retryDisabledReason}</p>}
        </div>
      )}
    </div>
  );
}
