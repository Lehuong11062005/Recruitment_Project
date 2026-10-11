import { Route, Routes } from 'react-router-dom'
import { ROLES } from './constants/roles'

import PrivateRoute from './components/PrivateRoute'
import GuestRoute from './components/GuestRoute'
import RootRedirect from './components/RootRedirect'
import CandidateLayout from './components/layouts/CandidateLayout'
import RecruiterLayout from './components/layouts/RecruiterLayout'
import AdminLayout from './components/layouts/AdminLayout'

import Login from './pages/auth/Login'
import Register from './pages/auth/Register'

import CandidateDashboard from './pages/candidate/CandidateDashboard'
import JobList from './pages/candidate/JobList'
import JobDetail from './pages/candidate/JobDetail'
import MyApplications from './pages/candidate/MyApplications'
import ApplicationDetail from './pages/candidate/ApplicationDetail'
import Chat from './pages/candidate/Chat'

import ManageJobs from './pages/recruiter/ManageJobs'
import Dashboard from './pages/admin/Dashboard'

import Forbidden from './pages/common/Forbidden'
import NotFound from './pages/common/NotFound'

// Routing phân quyền: Candidate, Recruiter, Admin
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<RootRedirect />} />

      {/* Công khai (chỉ khi chưa đăng nhập) */}
      <Route element={<GuestRoute />}>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
      </Route>

      {/* Ứng viên */}
      <Route element={<PrivateRoute allowedRoles={[ROLES.CANDIDATE]} />}>
        <Route path="/candidate" element={<CandidateLayout />}>
          <Route index element={<CandidateDashboard />} />
          <Route path="jobs" element={<JobList />} /> {/* UC-C4 */}
          <Route path="jobs/:jobId" element={<JobDetail />} /> {/* UC-C5 */}
          <Route path="applications" element={<MyApplications />} /> {/* UC-C7 */}
          <Route path="applications/:applicationId" element={<ApplicationDetail />} />
          <Route path="messages" element={<Chat />} /> {/* UC-C8 */}
          <Route path="messages/:conversationId" element={<Chat />} />
        </Route>
      </Route>

      {/* Nhà tuyển dụng */}
      <Route element={<PrivateRoute allowedRoles={[ROLES.RECRUITER]} />}>
        <Route path="/recruiter" element={<RecruiterLayout />}>
          <Route index element={<ManageJobs />} />
        </Route>
      </Route>

      {/* Quản trị viên */}
      <Route element={<PrivateRoute allowedRoles={[ROLES.ADMIN]} />}>
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<Dashboard />} />
        </Route>
      </Route>

      <Route path="/403" element={<Forbidden />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}
