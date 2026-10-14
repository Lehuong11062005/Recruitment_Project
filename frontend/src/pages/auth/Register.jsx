import { Link } from 'react-router-dom'
import PagePlaceholder from '../../components/PagePlaceholder'

// UC-C1 / UC-R1. Backend: authService.register({ email, password, full_name, phone, user_type })
export default function Register() {
  return (
    <div className="mx-auto max-w-xl px-4 py-10">
      <PagePlaceholder
        code="UC-C1"
        title="Đăng ký"
        description="Trang đăng ký, sẽ làm sau."
        todo={['Form: email, mật khẩu (tối thiểu 8 ký tự), họ tên, số điện thoại, loại tài khoản (Ứng viên / Nhà tuyển dụng)']}
      />
      <Link to="/login" className="mt-4 inline-block text-sm text-blue-600 hover:underline">
        Quay lại đăng nhập
      </Link>
    </div>
  )
}
