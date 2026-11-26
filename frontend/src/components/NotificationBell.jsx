import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Icon from './Icon';
import { notificationService } from '../services/notificationService';

function formatRelativeTime(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleString('vi-VN', {
    hour: '2-digit',
    minute: '2-digit',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}

export default function NotificationBell() {
  const navigate = useNavigate();
  const containerRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchLatest = useCallback(() => {
    return notificationService.getNotifications({ limit: 20 }).then((result) => {
      setItems(Array.isArray(result) ? result : []);
      setError('');
    });
  }, []);

  useEffect(() => {
    let active = true;
    notificationService
      .getNotifications({ limit: 20 })
      .then((result) => {
        if (active) setItems(Array.isArray(result) ? result : []);
      })
      .catch(() => {});

    const interval = window.setInterval(() => {
      notificationService
        .getNotifications({ limit: 20 })
        .then((result) => {
          if (active) setItems(Array.isArray(result) ? result : []);
        })
        .catch(() => {});
    }, 20000);

    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    if (!open) return undefined;
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setOpen(false);
      }
    };
    const handleEscape = (event) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    window.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      window.removeEventListener('keydown', handleEscape);
    };
  }, [open]);

  const unreadCount = items.filter((item) => !item.is_read).length;

  const toggleOpen = () => {
    const next = !open;
    setOpen(next);
    if (next) {
      setLoading(true);
      setError('');
      fetchLatest()
        .catch((err) => {
          setError(err?.message || 'Không thể tải thông báo.');
        })
        .finally(() => {
          setLoading(false);
        });
    }
  };

  const handleSelect = async (item) => {
    if (!item.is_read) {
      try {
        const updated = await notificationService.markAsRead(item.id);
        setItems((prev) =>
          prev.map((row) =>
            String(row.id) === String(item.id) ? { ...row, is_read: updated.is_read ?? true } : row
          )
        );
      } catch {
        // Không chặn điều hướng nếu đánh dấu đã đọc gặp lỗi mạng tạm thời
      }
    }
    setOpen(false);
    if (item.action_url) {
      navigate(item.action_url);
    }
  };

  return (
    <div className="notif-wrapper" ref={containerRef}>
      <button
        type="button"
        className="icon-button notif-trigger"
        aria-label="Thông báo"
        aria-expanded={open}
        onClick={toggleOpen}
        title="Thông báo"
      >
        <Icon name="bell" size={18} />
        {unreadCount > 0 && (
          <span className="notif-badge" aria-label={`${unreadCount} thông báo chưa đọc`}>
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <section className="notif-dropdown" aria-label="Danh sách thông báo">
          <div className="notif-head">
            <strong>Thông báo</strong>
            <span className="badge badge-blue">{unreadCount} chưa đọc</span>
          </div>

          {error && (
            <div className="alert-box alert-error notif-alert" role="alert">
              {error}
            </div>
          )}

          {loading && items.length === 0 ? (
            <div className="notif-empty" role="status">
              Đang tải thông báo...
            </div>
          ) : items.length === 0 ? (
            <div className="notif-empty">Chưa có thông báo nào.</div>
          ) : (
            <ul className="notif-list">
              {items.map((item) => (
                <li key={String(item.id)}>
                  <button
                    type="button"
                    className={`notif-item ${item.is_read ? '' : 'unread'}`}
                    onClick={() => handleSelect(item)}
                  >
                    <div className="notif-item-top">
                      <strong>{item.title}</strong>
                      {!item.is_read && <span className="notif-dot" aria-hidden="true" />}
                    </div>
                    <p>{item.content}</p>
                    <small>{formatRelativeTime(item.created_at)}</small>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  );
}
