import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { ROLE_HOME, ROLES } from '../../constants/roles'
import { useAuth } from '../../hooks/useAuth'
import { getErrorMessage } from '../../utils/http'

export default function Login() {
  const { login, mockLogin, isMockAuth } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const redirectAfterLogin = (user) => {
    // Quay lại trang đang định vào nếu có, ngược lại về trang chủ theo vai trò
    const from = location.state?.from?.pathname
    navigate(from ?? ROLE_HOME[user.role] ?? '/', { replace: true })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      redirectAfterLogin(await login(form))
    } catch (err) {
      setError(getErrorMessage(err, 'Đăng nhập thất bại'))
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value })

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="mb-4 text-center text-2xl font-bold text-blue-700">Đăng nhập</h1>

        <form onSubmit={handleSubmit} className="space-y-3">
          <input
            name="email"
            type="email"
            required
            placeholder="Email"
            value={form.email}
            onChange={handleChange}
            className="w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-blue-500"
          />
          <input
            name="password"
            type="password"
            required
            placeholder="Mật khẩu"
            value={form.password}
            onChange={handleChange}
            className="w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-blue-500"
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-blue-600 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {loading ? 'Đang đăng nhập...' : 'Đăng nhập'}
          </button>
        </form>

        {isMockAuth && (
          <div className="mt-5 border-t border-slate-200 pt-4">
            <p className="mb-2 text-center text-xs text-slate-500">
              Chế độ thử (VITE_MOCK_AUTH=true): vào thẳng với vai trò
            </p>
            <div className="grid grid-cols-3 gap-2">
              {Object.values(ROLES).map((role) => (
                <button
                  key={role}
                  onClick={() => redirectAfterLogin(mockLogin(role))}
                  className="rounded-md border border-slate-300 py-1.5 text-xs hover:bg-slate-100"
                >
                  {role}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
