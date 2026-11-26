import { useEffect, useState } from 'react';

const PAGE_SIZE = 20;

export default function AdminList({
  label,
  load,
  fields,
  searchLabel,
  columns,
  renderCells,
  tableClass = '',
}) {
  const initialDraft = Object.fromEntries([
    ...(searchLabel ? [['q', '']] : []),
    ...fields.map(({ name }) => [name, '']),
  ]);

  const [draftFilters, setDraftFilters] = useState(initialDraft);
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
    const activeEntries = Object.entries(draftFilters)
      .map(([key, val]) => [key, (val || '').trim()])
      .filter(([, val]) => Boolean(val));
    setNotice('');
    setError('');
    setLoading(true);
    setFilters({ ...Object.fromEntries(activeEntries), page: 1 });
  }

  function resetFilters() {
    setDraftFilters(initialDraft);
    setNotice('');
    setError('');
    setLoading(true);
    setFilters({ page: 1 });
  }

  const hasActiveFilter = Object.entries(filters).some(
    ([key, val]) => key !== 'page' && Boolean(val)
  ) || Object.values(draftFilters).some((val) => Boolean((val || '').trim()));

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
      <div className="admin-list-head">
        <h2>{label}</h2>
        {data && <span className="badge badge-gray">{data.total} bản ghi</span>}
      </div>

      <form className="admin-filters" onSubmit={applyFilters} aria-label={`Bộ lọc ${label}`}>
        {searchLabel && (
          <label className="admin-search-field">
            {searchLabel}
            <input
              className="form-input"
              name="q"
              type="search"
              maxLength={254}
              placeholder="Nhập từ khóa tìm kiếm..."
              value={draftFilters.q ?? ''}
              onChange={(e) => setDraftFilters((prev) => ({ ...prev, q: e.target.value }))}
            />
          </label>
        )}
        {fields.map(({ name, title, options }) => (
          <label key={name}>
            {title}
            <select
              className="form-input"
              name={name}
              value={draftFilters[name] ?? ''}
              onChange={(e) => setDraftFilters((prev) => ({ ...prev, [name]: e.target.value }))}
            >
              <option value="">Tất cả</option>
              {Object.entries(options).map(([value, text]) => (
                <option key={value} value={value}>
                  {text}
                </option>
              ))}
            </select>
          </label>
        ))}
        <div className="admin-filter-actions">
          <button type="submit" className="btn btn-primary" disabled={busy}>
            Áp dụng
          </button>
          {hasActiveFilter && (
            <button type="button" className="btn btn-secondary" disabled={busy} onClick={resetFilters}>
              Đặt lại
            </button>
          )}
        </div>
      </form>

      {notice && (
        <p className="alert-box alert-success" role="status">
          {notice}
        </p>
      )}
      {error && (
        <div className="alert-box alert-error" role="alert">
          {error}{' '}
          {!data && (
            <button type="button" className="btn btn-secondary" onClick={refresh}>
              Thử lại
            </button>
          )}
        </div>
      )}

      {loading ? (
        <div className="empty-state" role="status">
          Đang tải dữ liệu…
        </div>
      ) : (
        data && (
          <>
            {data.items.length === 0 ? (
              <div className="empty-state">
                <strong>Không tìm thấy kết quả phù hợp</strong>
                <p>Hãy thử thay đổi điều kiện lọc hoặc từ khóa tìm kiếm.</p>
              </div>
            ) : (
              <div className="admin-table-wrap">
                <table className={tableClass} aria-label={label}>
                  <thead>
                    <tr>
                      {columns.map((column) => (
                        <th key={column} scope="col">
                          {column}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.map((item) => (
                      <tr key={item.id}>{renderCells(item, runAction, busy)}</tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {data.total > 0 && (
              <div className="admin-pagination">
                <span className="muted small">
                  Trang {data.page} / {Math.max(1, Math.ceil(data.total / PAGE_SIZE))} · Tổng cộng {data.total} kết quả
                </span>
                <div className="button-row">
                  <button
                    type="button"
                    className="btn btn-secondary"
                    disabled={busy || data.page === 1}
                    onClick={() => goToPage(data.page - 1)}
                  >
                    Trước
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    disabled={busy || data.page * PAGE_SIZE >= data.total}
                    onClick={() => goToPage(data.page + 1)}
                  >
                    Sau
                  </button>
                </div>
              </div>
            )}
          </>
        )
      )}
    </section>
  );
}
