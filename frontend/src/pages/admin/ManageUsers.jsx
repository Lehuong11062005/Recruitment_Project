import { useAuth } from '../../hooks/useAuth';
import { adminService } from '../../services/adminService';
import AdminList from './AdminList';
import StatusBadge from './StatusBadge';

const USER_TYPES = { CANDIDATE: 'Ứng viên', RECRUITER: 'Nhà tuyển dụng' };
const ROLES = { USER: 'Người dùng', ADMIN: 'Quản trị viên' };
const FIELDS = [
  { name: 'role', title: 'Vai trò', options: ROLES },
  { name: 'user_type', title: 'Loại tài khoản', options: USER_TYPES },
  { name: 'status', title: 'Trạng thái', options: { ACTIVE: 'Hoạt động', BANNED: 'Đã khóa' } },
];

export default function ManageUsers() {
  const { user } = useAuth();
  return (
    <AdminList
      label="Danh sách người dùng"
      load={adminService.listUsers}
      fields={FIELDS}
      searchLabel="Tìm theo tên hoặc email"
      columns={['Tài khoản', 'Vai trò', 'Loại tài khoản', 'Trạng thái', 'Thao tác']}
      renderCells={(item, runAction, busy) => {
        const banned = item.status === 'BANNED';
        return (
          <>
            <td><strong>{item.full_name}</strong><small>{item.email}</small></td>
            <td>{ROLES[item.role] || item.role}</td>
            <td>{USER_TYPES[item.user_type] || '—'}</td>
            <td><StatusBadge value={item.status} /></td>
            <td>
              {item.id === user?.id ? <small>Tài khoản của bạn</small> : (
                <button
                  type="button"
                  className={`btn btn-secondary ${banned ? '' : 'danger-text'}`}
                  disabled={busy}
                  onClick={() => runAction(
                    () => adminService.updateUserStatus(item.id, banned ? 'ACTIVE' : 'BANNED'),
                    banned ? null : `Khóa tài khoản ${item.email}?`,
                  )}
                >{banned ? 'Mở khóa' : 'Khóa'}</button>
              )}
            </td>
          </>
        );
      }}
    />
  );
}
