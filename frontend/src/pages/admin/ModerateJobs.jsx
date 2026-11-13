import { adminService } from '../../services/adminService';
import AdminList from './AdminList';
import StatusBadge from './StatusBadge';

const FIELDS = [{
  name: 'status',
  title: 'Trạng thái tin',
  options: { OPEN: 'Đang tuyển', CLOSED: 'Đã đóng', HIDDEN: 'Đã ẩn' },
}];

export default function ModerateJobs() {
  return (
    <AdminList
      label="Danh sách tin tuyển dụng"
      load={adminService.listJobs}
      fields={FIELDS}
      columns={['Tin tuyển dụng', 'Nội dung', 'Trạng thái', 'Thao tác']}
      renderCells={(item, runAction, busy) => (
        <>
          <td><strong>{item.title}</strong><small>{item.company_name || '—'}</small><small>{item.location}</small></td>
          <td><details><summary>Xem mô tả</summary><p className="admin-description">{item.description}</p></details></td>
          <td><StatusBadge value={item.status} /></td>
          <td>
            <div className="button-row">
              {item.status !== 'HIDDEN' && (
                <button type="button" className="btn btn-secondary" disabled={busy}
                  onClick={() => runAction(() => adminService.moderateJob(item.id, 'HIDDEN'), `Ẩn tin “${item.title}”?`)}>
                  Ẩn tin
                </button>
              )}
              <button type="button" className="btn btn-secondary danger-text" disabled={busy}
                onClick={() => runAction(() => adminService.moderateJob(item.id, 'DELETED'), `Xóa mềm tin “${item.title}”? Tin sẽ biến mất khỏi danh sách.`)}>
                Xóa mềm
              </button>
            </div>
          </td>
        </>
      )}
    />
  );
}
