import { useEffect, useState } from 'react';

const PAGE_SIZE = 20;

export default function AdminList({ label, load, fields, searchLabel, columns, renderCells }) {
  const [filters, setFilters] = useState({ page: 1 });
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    load({ ...filters, limit: PAGE_SIZE }, controller.signal)
      .then((result) => {
        if (controller.signal.aborted) return;
        const lastPage = Math.max(1, Math.ceil(result.total / PAGE_SIZE));
        if (filters.page > lastPage) {
          setFilters({ ...filters, page: lastPage });
          return;
        }
        setData(result);
        setLoading(false);
      })
      .catch((failure) => {
        if (controller.signal.aborted) return;
        setError(failure.message);
        setData(null);
        setLoading(false);
      });
    return () => controller.abort();
  }, [filters, load, revision]);

  function refresh() {
    setError('');
    setLoading(true);
    setRevision((value) => value + 1);
  }

  function goToPage(page) {
    setError('');
    setLoading(true);
    setFilters({ ...filters, page });
  }

  function applyFilters(event) {
    event.preventDefault();
    const values = Object.fromEntries(
      [...new FormData(event.currentTarget)].filter(([, value]) => value.trim()),
    );
    setNotice('');
    setError('');
    setLoading(true);
    setFilters({ ...values, page: 1 });
  }

  async function runAction(action, confirmation) {
    if (confirmation && !window.confirm(confirmation)) return;
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await action();
      setNotice('Đã cập nhật thành công.');
      refresh();
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card admin-list">
      <form className="admin-filters" onSubmit={applyFilters} aria-label={`Bộ lọc ${label}`}>
        {searchLabel && (
          <label>
            {searchLabel}
            <input className="form-input" name="q" type="search" maxLength={254} />
          </label>
        )}
        {fields.map(({ name, title, options }) => (
          <label key={name}>
            {title}
            <select className="form-input" name={name}>
              <option value="">Tất cả</option>
              {Object.entries(options).map(([value, text]) => <option key={value} value={value}>{text}</option>)}
            </select>
          </label>
        ))}
        <button className="btn btn-primary" disabled={busy}>Áp dụng</button>
      </form>
      {notice && <p className="alert-box alert-success" role="status">{notice}</p>}
      {error && (
        <div className="alert-box alert-error" role="alert">
          {error}
          {!data && <button type="button" className="btn btn-secondary" onClick={refresh}>Thử lại</button>}
        </div>
      )}
      {loading ? <p role="status">Đang tải dữ liệu…</p> : data && (
        <>
          {data.items.length === 0 ? <p className="muted">Không tìm thấy kết quả phù hợp.</p> : (
            <div className="admin-table-wrap">
              <table aria-label={label}>
                <thead><tr>{columns.map((column) => <th key={column} scope="col">{column}</th>)}</tr></thead>
                <tbody>
                  {data.items.map((item) => <tr key={item.id}>{renderCells(item, runAction, busy)}</tr>)}
                </tbody>
              </table>
            </div>
          )}
          {data.total > 0 && (
            <div className="admin-pagination">
              <span className="muted">Trang {data.page} / {Math.ceil(data.total / PAGE_SIZE)} · {data.total} kết quả</span>
              <div className="button-row">
                <button type="button" className="btn btn-secondary" disabled={busy || data.page === 1} onClick={() => goToPage(data.page - 1)}>Trước</button>
                <button type="button" className="btn btn-secondary" disabled={busy || data.page * PAGE_SIZE >= data.total} onClick={() => goToPage(data.page + 1)}>Sau</button>
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}
