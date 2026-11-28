import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import Icon from '../../components/Icon';
import { useAuth } from '../../hooks/useAuth';
import { jobService } from '../../services/jobService';

const DEFAULT_WEIGHTS_PCT = {
  skill_pct: '50',
  semantic_pct: '35',
  experience_pct: '15',
};

const WEIGHT_CRITERIA = [
  {
    field: 'skill_pct',
    weightKey: 'skill_weight',
    tone: 'blue',
    title: 'Mức độ phù hợp kỹ năng (Skill Score)',
    hint: 'So khớp danh sách kỹ năng trích xuất từ CV với các kỹ năng bắt buộc của tin tuyển dụng.',
  },
  {
    field: 'semantic_pct',
    weightKey: 'semantic_weight',
    tone: 'purple',
    title: 'Mức độ tương đồng ngữ nghĩa (Semantic Score)',
    hint: 'Đo độ tương thích ngữ cảnh dự án, vai trò và mô tả công việc bằng mô hình Sentence-BERT.',
  },
  {
    field: 'experience_pct',
    weightKey: 'experience_weight',
    tone: 'teal',
    title: 'Mức độ phù hợp kinh nghiệm (Experience Score)',
    hint: 'Đối chiếu tổng số năm kinh nghiệm làm việc của ứng viên với mức tối thiểu yêu cầu.',
  },
];

const emptyForm = {
  title: '',
  description: '',
  location: '',
  level: 'MID',
  experience_required: '0',
  salary_min: '',
  salary_max: '',
  currency: 'VND',
  ...DEFAULT_WEIGHTS_PCT,
};

const formatPctNumber = (ratio, fallbackPct) => {
  const num = Number(ratio);
  if (!Number.isFinite(num)) return String(fallbackPct);
  const pct = Math.round(num * 10000) / 100;
  return String(pct);
};

const weightsToFormPct = (weights) => ({
  skill_pct: formatPctNumber(weights?.skill_weight, 50),
  semantic_pct: formatPctNumber(weights?.semantic_weight, 35),
  experience_pct: formatPctNumber(weights?.experience_weight, 15),
});

const validateWeightsForm = (form) => {
  const rawValues = [
    { label: 'Kỹ năng', raw: String(form.skill_pct ?? '').trim() },
    { label: 'Ngữ nghĩa', raw: String(form.semantic_pct ?? '').trim() },
    { label: 'Kinh nghiệm', raw: String(form.experience_pct ?? '').trim() },
  ];

  for (const item of rawValues) {
    if (item.raw === '') {
      return {
        valid: false,
        total: 0,
        skill: 0,
        semantic: 0,
        experience: 0,
        message: `Vui lòng nhập trọng số phần trăm cho tiêu chí ${item.label}.`,
      };
    }
    const parsed = Number(item.raw);
    if (!Number.isFinite(parsed)) {
      return {
        valid: false,
        total: 0,
        skill: 0,
        semantic: 0,
        experience: 0,
        message: `Trọng số ${item.label} phải là số hợp lệ.`,
      };
    }
    if (parsed < 0 || parsed > 100) {
      return {
        valid: false,
        total: parsed,
        skill: Math.max(0, Number(form.skill_pct) || 0),
        semantic: Math.max(0, Number(form.semantic_pct) || 0),
        experience: Math.max(0, Number(form.experience_pct) || 0),
        message: `Trọng số ${item.label} phải nằm trong khoảng từ 0% đến 100%.`,
      };
    }
  }

  const skill = Number(rawValues[0].raw);
  const semantic = Number(rawValues[1].raw);
  const experience = Number(rawValues[2].raw);
  const total = Math.round((skill + semantic + experience) * 100) / 100;

  if (Math.abs(total - 100) > 0.01) {
    const diff = Math.round((100 - total) * 100) / 100;
    const hint = diff > 0 ? `còn thiếu ${diff}%` : `đang vượt ${Math.abs(diff)}%`;
    return {
      valid: false,
      total,
      skill,
      semantic,
      experience,
      message: `Tổng trọng số hiện là ${total}% (${hint}). Tổng 3 tiêu chí bắt buộc bằng đúng 100%.`,
    };
  }

  return {
    valid: true,
    total: 100,
    skill,
    semantic,
    experience,
    message: '',
    payload: {
      skill_weight: Math.round(skill * 100) / 10000,
      semantic_weight: Math.round(semantic * 100) / 10000,
      experience_weight: Math.round(experience * 100) / 10000,
    },
  };
};

const formatJobWeightsSummary = (job) => {
  const w = job?.matching_weights;
  const s = formatPctNumber(w?.skill_weight, 50);
  const sem = formatPctNumber(w?.semantic_weight, 35);
  const exp = formatPctNumber(w?.experience_weight, 15);
  return `${s}% · ${sem}% · ${exp}%`;
};

const getRows = (response) => {
  if (Array.isArray(response)) return response;
  if (Array.isArray(response?.data)) return response.data;
  return [];
};

const getJobId = (job) => String(job.id || job._id);

const formatSalary = (salary) => {
  if (!salary) return 'Thỏa thuận';
  const minimum = Number(salary.min || 0).toLocaleString('vi-VN');
  const maximum = Number(salary.max || 0).toLocaleString('vi-VN');
  return `${minimum} - ${maximum} ${salary.currency || 'VND'}`;
};

export default function ManageJobs() {
  const { user } = useAuth();
  const [jobs, setJobs] = useState([]);
  const [skills, setSkills] = useState([]);
  const [selectedSkills, setSelectedSkills] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editingJob, setEditingJob] = useState(null);
  const [query, setQuery] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [updatingId, setUpdatingId] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const weightsValidation = useMemo(() => validateWeightsForm(form), [form]);
  const isDefaultWeights = (
    Number(form.skill_pct) === 50 &&
    Number(form.semantic_pct) === 35 &&
    Number(form.experience_pct) === 15
  );

  const loadJobs = useCallback(async () => {
    setLoading(true);
    try {
      const response = await jobService.getMyJobs();
      setJobs(getRows(response));
      setError('');
    } catch (requestError) {
      setError(requestError.message || 'Không thể tải danh sách tin tuyển dụng.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    jobService.getMyJobs()
      .then((response) => {
        if (active) setJobs(getRows(response));
      })
      .catch((requestError) => {
        if (active) setError(requestError.message || 'Không thể tải danh sách tin tuyển dụng.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    jobService.getSkills({ limit: 200 })
      .then((response) => {
        if (active) setSkills(getRows(response));
      })
      .catch((requestError) => {
        if (active) setError(requestError.message || 'Không thể tải danh mục kỹ năng.');
      });
    return () => {
      active = false;
    };
  }, []);

  const visibleJobs = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase('vi');
    return jobs.filter((job) => (
      `${job.title || ''} ${job.location || ''}`
        .toLocaleLowerCase('vi')
        .includes(normalizedQuery)
    ));
  }, [jobs, query]);

  const openCreateForm = () => {
    setEditingJob(null);
    setForm(emptyForm);
    setSelectedSkills([]);
    setError('');
    setModalOpen(true);
  };

  const openEditForm = (job) => {
    setEditingJob(job);
    setForm({
      ...emptyForm,
      title: job.title || '',
      description: job.description || '',
      location: job.location || '',
      level: job.level || 'MID',
      experience_required: String(job.experience_required ?? 0),
      salary_min: job.salary?.min == null ? '' : String(job.salary.min),
      salary_max: job.salary?.max == null ? '' : String(job.salary.max),
      currency: job.salary?.currency || 'VND',
      ...weightsToFormPct(job.matching_weights),
    });
    setSelectedSkills(Array.isArray(job.required_skills) ? job.required_skills.map(String) : []);
    setError('');
    setModalOpen(true);
  };

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  };

  const resetDefaultWeights = () => {
    setForm((current) => ({
      ...current,
      ...DEFAULT_WEIGHTS_PCT,
    }));
  };

  const toggleSkill = (skillId) => {
    setSelectedSkills((current) => (
      current.includes(skillId)
        ? current.filter((selected) => selected !== skillId)
        : [...current, skillId]
    ));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!weightsValidation.valid) {
      setError(weightsValidation.message);
      return;
    }
    setSaving(true);
    setError('');
    setNotice('');
    const salary = form.salary_min || form.salary_max
      ? {
          min: Number(form.salary_min) || 0,
          max: Number(form.salary_max) || 0,
          currency: form.currency,
        }
      : null;
    const payload = {
      title: form.title.trim(),
      description: form.description.trim(),
      location: form.location.trim() || null,
      level: form.level,
      experience_required: Number(form.experience_required) || 0,
      salary,
      required_skills: selectedSkills,
      matching_weights: weightsValidation.payload,
    };

    try {
      if (editingJob) {
        await jobService.updateJob(getJobId(editingJob), payload);
        setNotice('Đã cập nhật tin tuyển dụng và cấu hình trọng số AI Matching.');
      } else {
        await jobService.createJob(payload);
        setNotice('Đăng tin tuyển dụng thành công!');
      }
      setModalOpen(false);
      await loadJobs();
    } catch (requestError) {
      setError(requestError.message || 'Không thể lưu tin tuyển dụng.');
    } finally {
      setSaving(false);
    }
  };

  const handleStatusChange = async (job, status) => {
    const jobId = getJobId(job);
    setUpdatingId(jobId);
    setError('');
    setNotice('');
    try {
      await jobService.updateJobStatus(jobId, status);
      setNotice('Đã cập nhật trạng thái tin tuyển dụng.');
      await loadJobs();
    } catch (requestError) {
      setError(requestError.message || 'Không thể cập nhật trạng thái tin tuyển dụng.');
    } finally {
      setUpdatingId('');
    }
  };

  const closeForm = () => {
    if (!saving) setModalOpen(false);
  };

  const barScale = Math.max(100, weightsValidation.skill + weightsValidation.semantic + weightsValidation.experience);

  return (
    <div className="content-stack recruiter-workspace">
      {!user?.company_id && (
        <div className="inline-alert alert-amber">
          <Icon name="warning" />
          <span>
            <strong>Chưa liên kết hồ sơ doanh nghiệp</strong>
            Tài khoản của bạn chưa có hồ sơ doanh nghiệp. Hãy hoàn thiện hồ sơ trước khi đăng tin.
          </span>
          <Link className="btn btn-secondary" to="/recruiter/company-profile">Hồ sơ công ty</Link>
        </div>
      )}
      {error && !modalOpen && <div className="alert-box alert-error" role="alert">{error}</div>}
      {notice && <div className="alert-box alert-success" role="status">{notice}</div>}

      <div className="recruiter-stats-grid">
        <section className="card recruiter-stat-card"><span className="recruiter-stat-icon"><Icon name="briefcase" /></span><div><span>Tổng tin</span><strong>{jobs.length}</strong><small>Đã lưu trên hệ thống</small></div></section>
        <section className="card recruiter-stat-card recruiter-stat-green"><span className="recruiter-stat-icon"><Icon name="eye" /></span><div><span>Đang tuyển</span><strong>{jobs.filter((job) => job.status === 'OPEN').length}</strong><small>Trạng thái OPEN</small></div></section>
        <section className="card recruiter-stat-card recruiter-stat-purple"><span className="recruiter-stat-icon"><Icon name="users" /></span><div><span>Lượt xem</span><strong>{jobs.reduce((total, job) => total + Number(job.views_count || 0), 0).toLocaleString('vi-VN')}</strong><small>Tổng lượt xem</small></div></section>
        <section className="card recruiter-stat-card recruiter-stat-amber"><span className="recruiter-stat-icon"><Icon name="file" /></span><div><span>Hồ sơ nhận được</span><strong>{jobs.reduce((total, job) => total + Number(job.applications_count || 0), 0).toLocaleString('vi-VN')}</strong><small>Tổng ứng tuyển</small></div></section>
      </div>

      <section className="card recruiter-card">
        <div className="card-header recruiter-jobs-header">
          <div>
            <h2 className="section-title">Tin tuyển dụng</h2>
            <p className="muted small">Đăng tin, chỉnh sửa nội dung, cấu hình trọng số AI và quản lý trạng thái tuyển dụng.</p>
          </div>
          <div className="top-actions">
            <button className="btn btn-secondary" type="button" onClick={loadJobs} disabled={loading}><Icon name="clock" size={16} /> Làm mới</button>
            <button className="btn btn-primary" type="button" onClick={openCreateForm} disabled={!user?.company_id}><Icon name="plus" size={16} /> Đăng tin mới</button>
          </div>
        </div>

        <div className="recruiter-table-toolbar">
          <label className="search-input recruiter-job-search">
            <Icon name="search" size={16} />
            <input aria-label="Tìm kiếm tin tuyển dụng" placeholder="Tìm theo vị trí hoặc địa điểm..." value={query} onChange={(event) => setQuery(event.target.value)} />
          </label>
          <span className="muted small">{visibleJobs.length} tin tuyển dụng</span>
        </div>

        <div className="application-table-wrap recruiter-table-wrap">
          <table className="application-table recruiter-jobs-table">
            <thead><tr><th>Vị trí</th><th>Cấp bậc</th><th>Lượt xem</th><th>Hồ sơ</th><th>Trạng thái</th><th>Ngày tạo</th><th>Thao tác</th></tr></thead>
            <tbody>
              {visibleJobs.map((job) => (
                <tr key={getJobId(job)}>
                  <td>
                    <strong>{job.title}</strong>
                    <span className="recruiter-job-location"><Icon name="map" size={13} />{job.location || 'Chưa cập nhật'} · {formatSalary(job.salary)}</span>
                    <span className="ai-weights-inline-pill" title="Trọng số đánh giá AI (Kỹ năng · Ngữ nghĩa · Kinh nghiệm)">
                      <Icon name="spark" size={12} /> AI: {formatJobWeightsSummary(job)}
                    </span>
                  </td>
                  <td><span className="status-badge">{job.level || 'MID'}</span></td>
                  <td>{Number(job.views_count || 0).toLocaleString('vi-VN')}</td>
                  <td>{Number(job.applications_count || 0).toLocaleString('vi-VN')}</td>
                  <td><select aria-label={`Trạng thái tin ${job.title}`} className="input job-status-select" value={job.status} disabled={updatingId === getJobId(job)} onChange={(event) => handleStatusChange(job, event.target.value)}><option value="OPEN">OPEN</option><option value="CLOSED">CLOSED</option><option value="HIDDEN">HIDDEN</option></select></td>
                  <td>{job.created_at ? new Date(job.created_at).toLocaleDateString('vi-VN') : '—'}</td>
                  <td><button className="btn btn-secondary" type="button" onClick={() => openEditForm(job)}>Chỉnh sửa</button> <Link className="btn btn-secondary" to={`/recruiter/jobs/${getJobId(job)}/applications`}>Xem ứng viên</Link></td>
                </tr>
              ))}
              {loading && <tr><td colSpan="7">Đang tải danh sách tin tuyển dụng...</td></tr>}
              {!loading && visibleJobs.length === 0 && (
                <tr><td colSpan="7"><div className="recruiter-table-empty"><span><Icon name="briefcase" size={22} /></span><strong>{jobs.length ? 'Không tìm thấy tin phù hợp' : 'Chưa có tin tuyển dụng'}</strong><p>{jobs.length ? 'Thử thay đổi từ khóa tìm kiếm.' : 'Đăng tin mới để bắt đầu tuyển dụng.'}</p></div></td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {modalOpen && (
        <div className="modal-backdrop recruiter-modal-backdrop" role="presentation" onMouseDown={(event) => {
          if (event.target === event.currentTarget) closeForm();
        }}>
          <section className="modal-card modal-wide recruiter-job-modal" role="dialog" aria-modal="true" aria-labelledby="recruiter-job-title">
            <div className="card-header recruiter-modal-header">
              <div><h2 className="section-title" id="recruiter-job-title">{editingJob ? 'Chỉnh sửa tin tuyển dụng' : 'Đăng tin tuyển dụng mới'}</h2><p className="muted small">Thông tin JD và trọng số tiêu chí được lưu riêng cho từng tin tuyển dụng.</p></div>
              <button className="btn btn-ghost recruiter-close-button" type="button" onClick={closeForm} disabled={saving}>Đóng</button>
            </div>
            {error && <div className="alert-box alert-error" role="alert">{error}</div>}
            <form onSubmit={handleSubmit}>
              <div className="job-form-grid recruiter-job-form-grid">
                <div className="content-stack compact">
                  <label className="form-field"><span>Tiêu đề công việc <b className="form-required">*</b></span><input className="input" name="title" value={form.title} onChange={handleChange} required /></label>
                  <label className="form-field"><span>Nội dung chi tiết (JD) <b className="form-required">*</b></span><textarea className="input textarea" name="description" rows={8} value={form.description} onChange={handleChange} required /></label>
                  <div className="form-field"><span>Kỹ năng yêu cầu</span><div className="taxonomy-list recruiter-skill-list">
                    {skills.map((skill) => {
                      const skillId = String(skill.id || skill._id);
                      return <button className={selectedSkills.includes(skillId) ? 'selected' : ''} key={skillId} type="button" onClick={() => toggleSkill(skillId)}>{selectedSkills.includes(skillId) && <Icon name="check" size={13} />}{skill.name}</button>;
                    })}
                    {!skills.length && <small className="muted">Danh mục kỹ năng hiện chưa có dữ liệu.</small>}
                  </div></div>
                </div>
                <div className="content-stack compact">
                  <div className="form-grid two">
                    <label className="form-field"><span>Địa điểm</span><input className="input" name="location" value={form.location} onChange={handleChange} /></label>
                    <label className="form-field"><span>Cấp bậc</span><select className="input" name="level" value={form.level} onChange={handleChange}><option value="JUNIOR">JUNIOR</option><option value="MID">MID</option><option value="SENIOR">SENIOR</option></select>
                    </label>
                    <label className="form-field"><span>Kinh nghiệm (năm)</span><input className="input" name="experience_required" type="number" min="0" value={form.experience_required} onChange={handleChange} /></label>
                    <label className="form-field"><span>Tiền tệ</span><select className="input" name="currency" value={form.currency} onChange={handleChange}><option value="VND">VND</option><option value="USD">USD</option></select></label>
                    <label className="form-field"><span>Lương tối thiểu</span><input className="input" name="salary_min" type="number" min="0" value={form.salary_min} onChange={handleChange} /></label>
                    <label className="form-field"><span>Lương tối đa</span><input className="input" name="salary_max" type="number" min="0" value={form.salary_max} onChange={handleChange} /></label>
                  </div>
                </div>
              </div>

              <section className="ai-weights-section" aria-labelledby="ai-weights-heading">
                <div className="ai-weights-head">
                  <div>
                    <h3 id="ai-weights-heading" className="ai-weights-title">
                      <Icon name="spark" size={16} /> Cấu hình tiêu chí đánh giá AI
                    </h3>
                    <p className="muted small">
                      Điều chỉnh tỷ trọng chấm điểm độ phù hợp CV – JD cho riêng vị trí này (mặc định 50% – 35% – 15%). Các hồ sơ đã chấm trước đó vẫn giữ nguyên điểm lịch sử.
                    </p>
                  </div>
                  <div className="ai-weights-head-actions">
                    <span
                      className={`badge ${weightsValidation.valid ? 'badge-green' : 'badge-red'}`}
                      data-testid="weights-total-badge"
                    >
                      Tổng trọng số: {weightsValidation.total}% / 100%
                    </span>
                    <button
                      type="button"
                      className="btn btn-secondary ai-weights-reset"
                      onClick={resetDefaultWeights}
                      disabled={saving || isDefaultWeights}
                    >
                      Khôi phục mặc định
                    </button>
                  </div>
                </div>

                <div className="ai-weights-stacked-bar" aria-hidden="true">
                  <span className="seg-blue" style={{ width: `${(Math.max(0, weightsValidation.skill) / barScale) * 100}%` }} />
                  <span className="seg-purple" style={{ width: `${(Math.max(0, weightsValidation.semantic) / barScale) * 100}%` }} />
                  <span className="seg-teal" style={{ width: `${(Math.max(0, weightsValidation.experience) / barScale) * 100}%` }} />
                </div>

                <div className="ai-weights-grid">
                  {WEIGHT_CRITERIA.map((criterion) => {
                    const numericVal = Math.max(0, Math.min(100, Number(form[criterion.field]) || 0));
                    return (
                      <div key={criterion.field} className={`ai-weight-card tone-${criterion.tone}`}>
                        <div className="ai-weight-card-top">
                          <label htmlFor={`input-${criterion.field}`} className="ai-weight-label">
                            {criterion.title}
                          </label>
                          <div className="ai-weight-pct-box">
                            <input
                              id={`input-${criterion.field}`}
                              aria-label={criterion.title}
                              className="input ai-weight-number"
                              name={criterion.field}
                              type="number"
                              step="any"
                              value={form[criterion.field]}
                              onChange={handleChange}
                            />
                            <span>%</span>
                          </div>
                        </div>
                        <input
                          aria-label={`Thanh trượt ${criterion.title}`}
                          className="ai-weight-slider"
                          name={criterion.field}
                          type="range"
                          min="0"
                          max="100"
                          step="1"
                          value={numericVal}
                          onChange={handleChange}
                        />
                        <p className="ai-weight-hint">{criterion.hint}</p>
                      </div>
                    );
                  })}
                </div>

                {!weightsValidation.valid && (
                  <div className="alert-box alert-error ai-weights-error" role="alert">
                    {weightsValidation.message}
                  </div>
                )}
              </section>

              <div className="modal-actions recruiter-modal-actions">
                <button className="btn btn-secondary" type="button" onClick={closeForm} disabled={saving}>Hủy</button>
                <button className="btn btn-primary" type="submit" disabled={saving || !weightsValidation.valid}>
                  {saving ? 'Đang lưu...' : editingJob ? 'Lưu thay đổi' : 'Đăng tin'}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}
