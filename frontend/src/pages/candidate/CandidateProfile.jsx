import { useEffect, useState } from 'react';
import { API_URL, CANDIDATE_DEMO_MODE } from '../../config/env';
import { DEMO_PROFILE } from '../../data/candidateDemo';
import { candidateProfileService } from '../../services/candidateProfileService';
import Icon from '../../components/Icon';

const EMPTY_PROFILE = {
  user_id: '', email: '', full_name: '', phone: '', summary: '', location: '',
  skills: [], experience: [], education: [], cv_url: null,
};
const MAX_CV_SIZE = 5 * 1024 * 1024;
const errorText = (error) => error?.message || 'Không thể thực hiện thao tác. Vui lòng thử lại.';

function normalizeProfile(profile) {
  return {
    ...EMPTY_PROFILE,
    ...(profile || {}),
    skills: Array.isArray(profile?.skills) ? profile.skills.map(String) : [],
    experience: Array.isArray(profile?.experience) ? profile.experience.map((item) => ({
      company: item.company || '', position: item.position || '', years: item.years ?? '', description: item.description || '',
    })) : [],
    education: Array.isArray(profile?.education) ? profile.education.map((item) => ({
      school: item.school || '', major: item.major || '', graduation_year: item.graduation_year ?? '',
    })) : [],
  };
}

function profilePayload(profile) {
  return {
    full_name: profile.full_name.trim(),
    phone: profile.phone.trim() || null,
    summary: profile.summary.trim() || null,
    location: profile.location.trim() || null,
    skills: profile.skills,
    experience: profile.experience
      .filter((item) => item.company.trim() || item.position.trim() || item.description.trim())
      .map((item) => ({ company: item.company.trim(), position: item.position.trim(), years: item.years === '' ? null : Number(item.years), description: item.description.trim() || null })),
    education: profile.education
      .filter((item) => item.school.trim() || item.major.trim() || item.graduation_year !== '')
      .map((item) => ({ school: item.school.trim(), major: item.major.trim() || null, graduation_year: item.graduation_year === '' ? null : Number(item.graduation_year) })),
  };
}

function cvHref(cvUrl) {
  if (!cvUrl) return '';
  if (/^https?:\/\//i.test(cvUrl)) return cvUrl;
  return `${API_URL.replace(/\/$/, '')}${cvUrl.startsWith('/') ? '' : '/'}${cvUrl}`;
}

export default function CandidateProfile() {
  const [profile, setProfile] = useState(normalizeProfile(EMPTY_PROFILE));
  const [skillsCatalog, setSkillsCatalog] = useState([]);
  const [suggestedSkills, setSuggestedSkills] = useState([]);
  const [loading, setLoading] = useState(!CANDIDATE_DEMO_MODE);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [success, setSuccess] = useState('');
  const [cvFile, setCvFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [cvError, setCvError] = useState('');
  const [cvSuccess, setCvSuccess] = useState('');

  useEffect(() => {
    let active = true;
    Promise.resolve().then(async () => {
      if (!active) return;
      setLoading(true);
      if (CANDIDATE_DEMO_MODE) {
        setProfile(normalizeProfile(DEMO_PROFILE));
        setSkillsCatalog([
          { id: 'demo-skill-js', name: 'JavaScript', category: 'Programming' },
          { id: 'demo-skill-react', name: 'React', category: 'Frontend' },
          { id: 'demo-skill-sql', name: 'SQL', category: 'Database' },
          { id: 'demo-skill-testing', name: 'Software Testing', category: 'Testing' },
        ]);
        setLoading(false);
        return;
      }
      const [profileResult, skillsResult] = await Promise.allSettled([
        candidateProfileService.getProfile(),
        candidateProfileService.getSkills(),
      ]);
      if (!active) return;
      if (profileResult.status === 'fulfilled') {
        setProfile(normalizeProfile(profileResult.value?.data ?? profileResult.value));
      } else {
        setProfile(normalizeProfile(EMPTY_PROFILE));
        setError(`Không tải được hồ sơ: ${errorText(profileResult.reason)}`);
      }
      if (skillsResult.status === 'fulfilled') {
        const rawSkills = skillsResult.value?.data ?? skillsResult.value;
        setSkillsCatalog(Array.isArray(rawSkills) ? rawSkills.map((skill) => ({ ...skill, id: String(skill.id ?? skill._id ?? '') })) : []);
      } else {
        setNotice(`Không tải được danh mục kỹ năng: ${errorText(skillsResult.reason)}`);
      }
      setLoading(false);
    }).catch((loadError) => {
      if (active) {
        setError(errorText(loadError));
        setLoading(false);
      }
    });
    return () => { active = false; };
  }, []);

  const updateField = (event) => {
    const { name, value } = event.target;
    setProfile((current) => ({ ...current, [name]: value }));
  };
  const toggleSkill = (id) => setProfile((current) => ({
    ...current,
    skills: current.skills.includes(id) ? current.skills.filter((item) => item !== id) : [...current.skills, id],
  }));
  const updateItem = (field, index, key, value) => setProfile((current) => ({
    ...current,
    [field]: current[field].map((item, currentIndex) => currentIndex === index ? { ...item, [key]: value } : item),
  }));
  const addItem = (field) => {
    const empty = field === 'experience'
      ? { company: '', position: '', years: '', description: '' }
      : { school: '', major: '', graduation_year: '' };
    setProfile((current) => ({ ...current, [field]: [...current[field], empty] }));
  };
  const removeItem = (field, index) => setProfile((current) => ({
    ...current,
    [field]: current[field].filter((_, currentIndex) => currentIndex !== index),
  }));

  const saveProfile = async (event) => {
    event.preventDefault();
    setError('');
    setSuccess('');
    if (!profile.full_name.trim()) { setError('Họ tên không được để trống.'); return; }
    if (CANDIDATE_DEMO_MODE) {
      setSuccess('Đã mô phỏng lưu hồ sơ. Dữ liệu chưa được gửi lên backend.');
      return;
    }
    setSaving(true);
    try {
      const result = await candidateProfileService.updateProfile(profilePayload(profile));
      setProfile(normalizeProfile(result?.data ?? result));
      setSuccess('Đã lưu hồ sơ trên máy chủ.');
    } catch (saveError) {
      setError(errorText(saveError));
    } finally {
      setSaving(false);
    }
  };

  const uploadCV = async () => {
    setCvError('');
    setCvSuccess('');
    setSuggestedSkills([]);
    if (!cvFile) { setCvError('Hãy chọn một file CV PDF.'); return; }
    if (cvFile.type !== 'application/pdf' && !cvFile.name.toLowerCase().endsWith('.pdf')) { setCvError('Chỉ chấp nhận file PDF.'); return; }
    if (cvFile.size > MAX_CV_SIZE) { setCvError('CV không được vượt quá 5 MB theo cấu hình Core Service.'); return; }
    if (CANDIDATE_DEMO_MODE) {
      setCvSuccess(`Đã mô phỏng chọn CV ${cvFile.name}; file chưa tải lên máy chủ.`);
      return;
    }
    setUploading(true);
    try {
      const result = await candidateProfileService.uploadCV(cvFile);
      const response = result?.data ?? result;
      setProfile((current) => ({ ...current, cv_url: response.cv_url || current.cv_url }));
      const suggestions = response.extraction?.suggested_skills || [];
      setSuggestedSkills(suggestions.map((skill) => ({ ...skill, id: String(skill.id ?? skill._id ?? '') })));
      const extractionStatus = response.extraction?.status;
      setCvSuccess(`Đã tải CV lên máy chủ: ${response.filename || cvFile.name}.${extractionStatus ? ` Phân tích CV: ${extractionStatus}.` : ''} Hãy rà soát gợi ý kỹ năng trước khi lưu hồ sơ.`);
    } catch (uploadError) {
      setCvError(errorText(uploadError));
    } finally {
      setUploading(false);
    }
  };

  const addSuggestedSkill = (skill) => {
    setProfile((current) => current.skills.includes(skill.id) ? current : { ...current, skills: [...current.skills, skill.id] });
    setSuggestedSkills((current) => current.filter((item) => item.id !== skill.id));
  };

  if (loading) return <section className="card text-center text-slate-500">Đang tải hồ sơ ứng viên…</section>;

  return (
    <div className="content-stack">
      <section className="card">
        <div className="flex flex-wrap items-start justify-between gap-3"><div><span className="badge badge-blue">Hồ sơ ứng viên</span><h2 className="display-title">Thông tin cá nhân</h2><p className="muted">Cập nhật thông tin, kỹ năng, kinh nghiệm, học vấn và CV.</p></div>{CANDIDATE_DEMO_MODE && <span className="badge badge-amber">DỮ LIỆU DEMO</span>}</div>
      </section>
      {error && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
      {notice && <div role="status" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">{notice}</div>}
      {success && <div role="status" className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{success}</div>}

      <form onSubmit={saveProfile} className="content-stack">
        <section className="card">
          <div className="card-header"><div><h3 className="section-title">Thông tin cơ bản</h3><p className="muted small">Thông tin này được dùng trong hồ sơ ứng viên.</p></div><Icon name="user" size={21} /></div>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block"><span className="mb-1 block text-sm font-semibold">Họ và tên *</span><input name="full_name" value={profile.full_name} onChange={updateField} required maxLength={100} className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm" /></label>
            <label className="block"><span className="mb-1 block text-sm font-semibold">Email</span><input value={profile.email || ''} readOnly className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-500" /><span className="muted mt-1 block text-xs">Email tài khoản không sửa ở màn hình này.</span></label>
            <label className="block"><span className="mb-1 block text-sm font-semibold">Số điện thoại</span><input name="phone" value={profile.phone || ''} onChange={updateField} maxLength={20} className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm" /></label>
            <label className="block"><span className="mb-1 block text-sm font-semibold">Địa điểm</span><input name="location" value={profile.location || ''} onChange={updateField} maxLength={200} placeholder="Hà Nội" className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm" /></label>
            <label className="block md:col-span-2"><span className="mb-1 block text-sm font-semibold">Giới thiệu bản thân</span><textarea name="summary" value={profile.summary || ''} onChange={updateField} rows={4} maxLength={2000} className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm" placeholder="Định hướng nghề nghiệp, kỹ năng nổi bật và mục tiêu…" /><span className="muted mt-1 block text-right text-xs">{(profile.summary || '').length}/2000</span></label>
          </div>
        </section>

        <section className="card">
          <div className="card-header"><div><h3 className="section-title">Kỹ năng</h3><p className="muted small">Kỹ năng được lưu bằng ID trong danh mục chuẩn của backend.</p></div><Icon name="check" size={21} /></div>
          {skillsCatalog.length === 0 ? <p className="muted text-sm">Chưa có danh mục kỹ năng để chọn.</p> : <div className="flex flex-wrap gap-2">{skillsCatalog.map((skill) => { const active = profile.skills.includes(String(skill.id)); return <button type="button" key={skill.id} onClick={() => toggleSkill(String(skill.id))} className={`rounded-full border px-3 py-1.5 text-sm ${active ? 'border-blue-600 bg-blue-50 font-semibold text-blue-700' : 'border-slate-300 text-slate-600 hover:border-blue-300'}`}>{active ? '✓ ' : '+ '}{skill.name}</button>; })}</div>}
        </section>

        <section className="card">
          <div className="flex flex-wrap items-center justify-between gap-3"><h3 className="section-title">Kinh nghiệm làm việc</h3><button type="button" className="btn btn-secondary" onClick={() => addItem('experience')}><Icon name="plus" size={15} />Thêm kinh nghiệm</button></div>
          {profile.experience.length === 0 && <p className="muted mt-3 text-sm">Chưa thêm kinh nghiệm.</p>}
          <div className="mt-4 space-y-4">{profile.experience.map((item, index) => <div key={`experience-${index}`} className="rounded-lg border border-slate-200 p-4"><div className="mb-3 flex items-center justify-between"><strong className="text-sm">Kinh nghiệm {index + 1}</strong><button type="button" className="text-sm text-red-600" onClick={() => removeItem('experience', index)}>Xóa</button></div><div className="grid gap-3 md:grid-cols-2"><label><span className="mb-1 block text-xs font-semibold">Công ty</span><input value={item.company} onChange={(event) => updateItem('experience', index, 'company', event.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></label><label><span className="mb-1 block text-xs font-semibold">Vị trí</span><input value={item.position} onChange={(event) => updateItem('experience', index, 'position', event.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></label><label><span className="mb-1 block text-xs font-semibold">Số năm kinh nghiệm</span><input type="number" min="0" max="60" step="0.5" value={item.years} onChange={(event) => updateItem('experience', index, 'years', event.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></label><label className="md:col-span-2"><span className="mb-1 block text-xs font-semibold">Mô tả</span><textarea rows={2} value={item.description} onChange={(event) => updateItem('experience', index, 'description', event.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></label></div></div>)}</div>
        </section>

        <section className="card">
          <div className="flex flex-wrap items-center justify-between gap-3"><h3 className="section-title">Học vấn</h3><button type="button" className="btn btn-secondary" onClick={() => addItem('education')}><Icon name="plus" size={15} />Thêm học vấn</button></div>
          {profile.education.length === 0 && <p className="muted mt-3 text-sm">Chưa thêm học vấn.</p>}
          <div className="mt-4 space-y-4">{profile.education.map((item, index) => <div key={`education-${index}`} className="rounded-lg border border-slate-200 p-4"><div className="mb-3 flex items-center justify-between"><strong className="text-sm">Học vấn {index + 1}</strong><button type="button" className="text-sm text-red-600" onClick={() => removeItem('education', index)}>Xóa</button></div><div className="grid gap-3 md:grid-cols-3"><label><span className="mb-1 block text-xs font-semibold">Trường học</span><input value={item.school} onChange={(event) => updateItem('education', index, 'school', event.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></label><label><span className="mb-1 block text-xs font-semibold">Chuyên ngành</span><input value={item.major} onChange={(event) => updateItem('education', index, 'major', event.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></label><label><span className="mb-1 block text-xs font-semibold">Năm tốt nghiệp</span><input type="number" min="1950" max="2100" value={item.graduation_year} onChange={(event) => updateItem('education', index, 'graduation_year', event.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></label></div></div>)}</div>
        </section>

        <div className="flex justify-end"><button type="submit" disabled={saving} className="btn btn-primary disabled:opacity-50">{saving ? 'Đang lưu…' : CANDIDATE_DEMO_MODE ? 'Mô phỏng lưu hồ sơ' : 'Lưu thay đổi'}</button></div>
      </form>

      <section className="card">
        <div className="card-header"><div><h3 className="section-title">CV ứng viên</h3><p className="muted small">Upload CV PDF để lưu vào profile và nhận gợi ý kỹ năng từ AI.</p></div><Icon name="file" size={21} /></div>
        {profile.cv_url ? <p className="mb-4 text-sm"><a className="text-blue-700 underline" href={cvHref(profile.cv_url)} target="_blank" rel="noreferrer">Mở CV hiện tại</a></p> : <p className="muted mb-4 text-sm">Chưa có CV được lưu.</p>}
        <label className="block"><span className="mb-1 block text-sm font-semibold">Chọn CV (PDF, tối đa 5 MB)</span><input type="file" accept=".pdf,application/pdf" onChange={(event) => { setCvFile(event.target.files?.[0] || null); setCvError(''); setCvSuccess(''); }} className="block w-full rounded-lg border border-slate-300 p-2 text-sm" />{cvFile && <span className="muted mt-1 block text-xs">Đã chọn: {cvFile.name}</span>}</label>
        {cvError && <div role="alert" className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{cvError}</div>}
        {cvSuccess && <div role="status" className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{cvSuccess}</div>}
        <button type="button" onClick={uploadCV} disabled={uploading} className="btn btn-primary mt-3 disabled:opacity-50"><Icon name="upload" size={15} />{uploading ? 'Đang tải CV…' : CANDIDATE_DEMO_MODE ? 'Mô phỏng upload CV' : 'Tải CV lên'}</button>
        {suggestedSkills.length > 0 && <div className="mt-5 rounded-lg border border-blue-200 bg-blue-50 p-4"><h4 className="font-bold text-blue-900">Kỹ năng AI gợi ý</h4><p className="muted mt-1 text-xs">Chỉ thêm vào form; cần bấm “Lưu thay đổi” để cập nhật hồ sơ.</p><div className="mt-3 flex flex-wrap gap-2">{suggestedSkills.map((skill) => <button type="button" key={skill.id} onClick={() => addSuggestedSkill(skill)} className="rounded-full border border-blue-300 bg-white px-3 py-1.5 text-sm text-blue-800">+ {skill.name}</button>)}</div></div>}
      </section>
    </div>
  );
}
