// Dữ liệu demo cho UI khi API Jobs chưa có route xử lý. Đây không phải dữ liệu DB thật.
export const DEMO_JOBS = [
  {
    id: '6610a1000000000000000001',
    title: 'Backend Developer (Python / FastAPI)',
    company_name: 'FPT Software',
    location: 'Hà Nội',
    level: 'MID',
    salary: { min: 20, max: 35, currency: 'triệu VND' },
    description: 'Phát triển REST API với Python/FastAPI, phối hợp với frontend và xây dựng kiểm thử cho các chức năng nghiệp vụ.',
    required_skills: ['Python', 'FastAPI', 'REST API'],
    experience_required: 1,
    status: 'OPEN',
    isDemo: true,
  },
  {
    id: '6610a1000000000000000002',
    title: 'Frontend Engineer (ReactJS)',
    company_name: 'VNG Corporation',
    location: 'TP. Hồ Chí Minh',
    level: 'JUNIOR',
    salary: { min: 15, max: 25, currency: 'triệu VND' },
    description: 'Xây dựng giao diện ReactJS, kết nối API và phối hợp với đội thiết kế để hoàn thiện trải nghiệm người dùng.',
    required_skills: ['React', 'JavaScript', 'HTML/CSS'],
    experience_required: 0,
    status: 'OPEN',
    isDemo: true,
  },
];

export const DEMO_PROFILE = {
  user_id: 'demo-candidate',
  email: 'candidate@demo.local',
  full_name: 'Nguyễn Văn Ứng Viên',
  phone: '0900000000',
  summary: 'Sinh viên Công nghệ thông tin quan tâm đến phát triển phần mềm.',
  location: 'Hà Nội',
  skills: [],
  experience: [{ company: '', position: '', years: '', description: '' }],
  education: [{ school: '', major: 'Công nghệ thông tin', graduation_year: '' }],
  cv_url: null,
};
