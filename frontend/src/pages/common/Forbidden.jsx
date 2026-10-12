import { Link } from 'react-router-dom'

export default function Forbidden() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-2">
      <h1 className="text-5xl font-bold text-red-600">403</h1>
      <p className="text-slate-600">Bạn không có quyền truy cập trang này.</p>
      <Link to="/" className="mt-2 text-blue-600 hover:underline">Về trang chủ</Link>
    </div>
  )
}
