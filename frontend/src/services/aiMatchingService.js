import api from './api';

// Routes và schema đã có trong ai-service/app/routers/ai_matching.py trên main.
export const aiMatchingService = {
  previewJobCV(jobId, file) {
    const formData = new FormData();
    formData.append('job_id', jobId);
    formData.append('file', file);
    return api.post('/api/v1/ai-analysis/preview', formData);
  },
  parseCV(file) {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/api/v1/ai/parse-cv', formData);
  },
  matchCVToJob(payload) {
    return api.post('/api/v1/ai/match', {
      cv_text: payload.cvText,
      jd_text: payload.jdText,
      candidate_skills: payload.candidateSkills || [],
      required_skills: payload.requiredSkills || [],
      candidate_experience_years: payload.candidateExperienceYears || 0,
      job_experience_required: payload.jobExperienceRequired || 0,
    });
  },
};
