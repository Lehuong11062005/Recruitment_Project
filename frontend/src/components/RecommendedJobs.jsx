import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Icon from './Icon';
import JobCard from './JobCard';
import { jobService } from '../services/jobService';

// jobService ném lỗi đồng bộ khi chưa cấu hình -> bọc để thành Promise rejection.
const safely = (fn) => new Promise((resolve) => resolve(fn()));

function RecommendedJobsInner({ onReload }) {
  const [state, setState] = useState({ phase: 'loading', items: [], message: '', error: '' });

  useEffect(() => {
    let active = true;
    safely(() => jobService.getRecommendations())
      .then((response) => {
        if (!active) return;
        const payload = response?.data ?? response;
        const items = Array.isArray(payload?.items) ? payload.items : [];
        setState({ phase: 'ready', items: items.slice(0, 5), message: payload?.message || '', error: '' });
      })
      .catch((error) => {
        if (active) setState({ phase: 'error', items: [], message: '', error: error?.message || 'Không thể tải gợi ý việc làm.' });
      });
    return () => { active = false; };
  }, []);

  return (
    <section className="card">
      <div className="card-header">
        <div>
          <span className="badge badge-purple"><Icon name="spark" size={13} /> AI gợi ý</span>
          <h3 className="section-title mt-2">Việc làm phù hợp với bạn (Top 5 AI Gợi ý)</h3>
          <p className="muted small">Xếp theo độ tương đồng giữa hồ sơ/CV của bạn và nội dung tin tuyển dụng.</p>
        </div>
      </div>

      {state.phase === 'loading' && (
        <div className="space-y-3 animate-pulse" aria-busy="true" role="status" aria-label="Đang tải gợi ý việc làm">
          {[0, 1, 2].map((i) => <div key={i} className="h-20 rounded-xl bg-slate-100" />)}
        </div>
      )}

      {state.phase === 'error' && (
        <div className="alert-box alert-error flex flex-wrap items-center justify-between gap-3" role="alert">
          <span>{state.error}</span>
          <button type="button" className="btn btn-secondary" onClick={onReload}>Thử lại</button>
        </div>
      )}

      {state.phase === 'ready' && state.items.length === 0 && (
        <div className="empty-state">
          <Icon name="spark" size={26} />
          <strong>Chưa có gợi ý việc làm</strong>
          <p>{state.message || 'Tải CV hoặc cập nhật hồ sơ để nhận gợi ý việc làm phù hợp.'}</p>
          <Link to="/candidate/profile" className="btn btn-secondary">Cập nhật hồ sơ</Link>
        </div>
      )}

      {state.phase === 'ready' && state.items.length > 0 && (
        <div className="job-catalog">
          {state.items.map((job) => (
            <JobCard
              key={job.id}
              job={job}
              badge={<span className="badge badge-purple">{Math.round(Number(job.match_score) || 0)}% Phù hợp</span>}
              footer={Array.isArray(job.matched_skills) && job.matched_skills.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {job.matched_skills.map((name) => <span key={name} className="badge badge-green">{name}</span>)}
                </div>
              )}
            />
          ))}
        </div>
      )}
    </section>
  );
}

export default function RecommendedJobs() {
  const [reloadKey, setReloadKey] = useState(0);
  return <RecommendedJobsInner key={reloadKey} onReload={() => setReloadKey((k) => k + 1)} />;
}
