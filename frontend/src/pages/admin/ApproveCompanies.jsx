import { adminService } from '../../services/adminService';
import AdminList from './AdminList';
import StatusBadge from './StatusBadge';

const FIELDS = [{
  name: 'verification_status',
  title: 'Trạng thái duyệt',
  options: { PENDING: 'Chờ duyệt', VERIFIED: 'Đã duyệt', REJECTED: 'Từ chối' },
}];

export default function ApproveCompanies() {
  return (
    <AdminList
      label="Danh sách doanh nghiệp"
      load={adminService.listCompanies}
      fields={FIELDS}
      columns={['Doanh nghiệp', 'Hồ sơ', 'Trạng thái', 'Thao tác']}
      renderCells={(item, runAction, busy) => (
        <>
          <td><strong>{item.name}</strong><small>{item.industry || '—'}</small><small>{item.address}</small></td>
          <td>
            <details>
              <summary>Xem hồ sơ</summary>
              <p className="admin-description">{item.description || 'Chưa có mô tả.'}</p>
              {item.website && <small>{item.website}</small>}
            </details>
          </td>
          <td><StatusBadge value={item.verification_status} /></td>
          <td>
            <div className="button-row">
              {item.verification_status !== 'VERIFIED' && (
                <button type="button" className="btn btn-primary" disabled={busy}
                  onClick={() => runAction(() => adminService.verifyCompany(item.id, 'VERIFIED'))}>
                  Duyệt
                </button>
              )}
              {item.verification_status !== 'REJECTED' && (
                <button type="button" className="btn btn-secondary danger-text" disabled={busy}
                  onClick={() => runAction(() => adminService.verifyCompany(item.id, 'REJECTED'), `Từ chối hồ sơ của ${item.name}?`)}>
                  Từ chối
                </button>
              )}
            </div>
          </td>
        </>
      )}
    />
  );
}
