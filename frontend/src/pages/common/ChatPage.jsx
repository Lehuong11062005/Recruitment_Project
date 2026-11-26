import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import Icon from '../../components/Icon';
import { WS_URL } from '../../config/env';
import { useAuth } from '../../hooks/useAuth';
import { chatService } from '../../services/chatService';
import { storage } from '../../utils/storage';

const WS_STATE_META = {
  idle: { label: 'Chưa chọn hội thoại', tone: 'badge-gray' },
  connecting: { label: 'Đang kết nối...', tone: 'badge-amber' },
  connected: { label: 'Đã kết nối realtime', tone: 'badge-green' },
  reconnecting: { label: 'Mất kết nối · Đang kết nối lại...', tone: 'badge-amber' },
  closed: { label: 'Ngắt kết nối', tone: 'badge-red' },
};

const FATAL_CLOSE_CODES = new Set([4401, 4403, 4404]);

const initials = (name = '') =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .slice(-2)
    .map((part) => part[0])
    .join('')
    .toUpperCase() || 'U';

function formatShortTime(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const now = new Date();
  const sameDay =
    date.getDate() === now.getDate() &&
    date.getMonth() === now.getMonth() &&
    date.getFullYear() === now.getFullYear();
  if (sameDay) {
    return date.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
  }
  return date.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });
}

function formatMessageTime(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleString('vi-VN', {
    hour: '2-digit',
    minute: '2-digit',
    day: '2-digit',
    month: '2-digit',
  });
}

function sortConversationsNewestFirst(list) {
  return [...list].sort((a, b) => {
    const ta = a.updated_at ? new Date(a.updated_at).getTime() : 0;
    const tb = b.updated_at ? new Date(b.updated_at).getTime() : 0;
    return tb - ta;
  });
}

export default function ChatPage() {
  const { user } = useAuth();
  const { conversationId: paramConvId } = useParams();
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();

  const queryConvId = searchParams.get('conversation_id') || '';
  const routeConvId = paramConvId || queryConvId || '';

  const baseChatPath = useMemo(() => {
    if (location.pathname.startsWith('/recruiter/messages')) return '/recruiter/messages';
    if (location.pathname.startsWith('/recruiter')) return '/recruiter/chat';
    if (location.pathname.startsWith('/candidate/messages')) return '/candidate/messages';
    return '/candidate/chat';
  }, [location.pathname]);

  const [conversations, setConversations] = useState([]);
  const [convLoading, setConvLoading] = useState(true);
  const [convError, setConvError] = useState('');
  const [search, setSearch] = useState('');

  const [manualSelectedId, setManualSelectedId] = useState('');
  const [messagesByConv, setMessagesByConv] = useState({});
  const [loadingConvId, setLoadingConvId] = useState('');
  const [msgErrorsByConv, setMsgErrorsByConv] = useState({});

  const [wsStatus, setWsStatus] = useState({ convId: '', state: 'idle', error: '' });
  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);

  const wsRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const activeConvRef = useRef('');
  const bottomRef = useRef(null);

  const refreshConversationsSilently = useCallback(() => {
    chatService
      .getConversations()
      .then((data) => {
        const rows = Array.isArray(data) ? sortConversationsNewestFirst(data) : [];
        setConversations(rows);
      })
      .catch(() => {});
  }, []);

  const handleRetryConversations = () => {
    setConvLoading(true);
    setConvError('');
    chatService
      .getConversations()
      .then((data) => {
        const rows = Array.isArray(data) ? sortConversationsNewestFirst(data) : [];
        setConversations(rows);
      })
      .catch((err) => {
        setConvError(err?.message || 'Không thể tải danh sách hội thoại.');
      })
      .finally(() => {
        setConvLoading(false);
      });
  };

  useEffect(() => {
    let active = true;
    chatService
      .getConversations()
      .then((data) => {
        if (!active) return;
        const rows = Array.isArray(data) ? sortConversationsNewestFirst(data) : [];
        setConversations(rows);
      })
      .catch((err) => {
        if (active) setConvError(err?.message || 'Không thể tải danh sách hội thoại.');
      })
      .finally(() => {
        if (active) setConvLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const activeId = String(routeConvId || manualSelectedId || conversations[0]?.id || '');

  useEffect(() => {
    activeConvRef.current = activeId;
  }, [activeId]);

  const activeConversation = useMemo(
    () => conversations.find((item) => String(item.id) === activeId) || null,
    [conversations, activeId]
  );

  const visibleConversations = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return conversations;
    return conversations.filter((conv) => {
      const target = `${conv.other_user?.full_name || ''} ${conv.job_title || ''} ${conv.last_message || ''}`.toLowerCase();
      return target.includes(q);
    });
  }, [conversations, search]);

  const currentMessages = useMemo(
    () => (activeId && Array.isArray(messagesByConv[activeId]) ? messagesByConv[activeId] : []),
    [messagesByConv, activeId]
  );

  // Đồng bộ lịch sử tin nhắn qua REST API mỗi khi đổi hội thoại
  useEffect(() => {
    if (!activeId) return undefined;

    let cancelled = false;
    Promise.resolve().then(() => {
      if (!cancelled) {
        setLoadingConvId(activeId);
        setMsgErrorsByConv((prev) => ({ ...prev, [activeId]: '' }));
      }
    });

    chatService
      .getMessages(activeId, { limit: 100 })
      .then((items) => {
        if (cancelled) return;
        const normalized = Array.isArray(items) ? items : [];
        setMessagesByConv((prev) => ({
          ...prev,
          [activeId]: normalized,
        }));
        setConversations((prev) =>
          prev.map((conv) => (String(conv.id) === activeId ? { ...conv, unread_count: 0 } : conv))
        );
      })
      .catch((err) => {
        if (cancelled) return;
        setMsgErrorsByConv((prev) => ({
          ...prev,
          [activeId]: err?.message || 'Không thể tải lịch sử tin nhắn.',
        }));
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingConvId((current) => (current === activeId ? '' : current));
        }
      });

    return () => {
      cancelled = true;
    };
  }, [activeId]);

  // Kết nối WebSocket qua API Gateway, chống tạo connection trùng lặp và tự động reconnect
  useEffect(() => {
    if (reconnectTimerRef.current) {
      window.clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (wsRef.current) {
      const prevWs = wsRef.current;
      wsRef.current = null;
      prevWs.onopen = null;
      prevWs.onmessage = null;
      prevWs.onerror = null;
      prevWs.onclose = null;
      try {
        prevWs.close(1000, 'Switching conversation');
      } catch {
        // ignore
      }
    }

    if (!activeId) return undefined;

    let disposed = false;
    let attempt = 0;

    const connect = () => {
      if (disposed) return;
      const token = storage.getToken();
      if (!token) {
        setWsStatus({
          convId: activeId,
          state: 'closed',
          error: 'Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.',
        });
        return;
      }

      setWsStatus({
        convId: activeId,
        state: attempt === 0 ? 'connecting' : 'reconnecting',
        error: '',
      });

      const cleanBase = WS_URL.replace(/\/+$/, '');
      const wsEndpoint = `${cleanBase}/ws/chat/${encodeURIComponent(activeId)}?token=${encodeURIComponent(token)}`;
      const socket = new WebSocket(wsEndpoint);
      wsRef.current = socket;

      socket.onopen = () => {
        if (disposed || wsRef.current !== socket) return;
        attempt = 0;
        setWsStatus({ convId: activeId, state: 'connected', error: '' });
      };

      socket.onmessage = (event) => {
        if (disposed || wsRef.current !== socket) return;
        try {
          const payload = JSON.parse(event.data);
          if (payload?.event === 'message' && payload.data) {
            const msg = payload.data;
            const msgConvId = String(msg.conversation_id || '');
            if (!msgConvId) return;

            setMessagesByConv((prev) => {
              const existing = Array.isArray(prev[msgConvId]) ? prev[msgConvId] : [];
              if (existing.some((item) => String(item.id) === String(msg.id))) {
                return prev;
              }
              return {
                ...prev,
                [msgConvId]: [...existing, msg],
              };
            });

            const previewText =
              (msg.content || '').trim() ||
              (msg.message_type === 'IMAGE' ? '[Hình ảnh]' : '[Tệp đính kèm]');

            setConversations((prev) => {
              const found = prev.some((c) => String(c.id) === msgConvId);
              if (!found) {
                refreshConversationsSilently();
                return prev;
              }
              const updated = prev.map((c) => {
                if (String(c.id) !== msgConvId) return c;
                const isIncoming = String(msg.sender_id) !== String(user?.id);
                const isViewing = activeConvRef.current === msgConvId;
                return {
                  ...c,
                  last_message: previewText,
                  updated_at: msg.created_at || new Date().toISOString(),
                  unread_count: isIncoming && !isViewing ? (c.unread_count || 0) + 1 : 0,
                };
              });
              return sortConversationsNewestFirst(updated);
            });

            if (
              msgConvId === activeConvRef.current &&
              String(msg.sender_id) !== String(user?.id) &&
              socket.readyState === WebSocket.OPEN
            ) {
              socket.send(JSON.stringify({ event: 'read' }));
            }
          } else if (payload?.event === 'error' && payload.detail) {
            setWsStatus((prev) => ({ ...prev, convId: activeId, error: String(payload.detail) }));
          }
        } catch {
          // ignore malformed frame
        }
      };

      socket.onerror = () => {
        if (disposed || wsRef.current !== socket) return;
      };

      socket.onclose = (closeEvent) => {
        if (disposed || wsRef.current !== socket) return;
        wsRef.current = null;
        if (FATAL_CLOSE_CODES.has(closeEvent.code)) {
          setWsStatus({
            convId: activeId,
            state: 'closed',
            error:
              closeEvent.code === 4401
                ? 'Xác thực WebSocket thất bại hoặc phiên làm việc đã hết hạn.'
                : 'Bạn không có quyền truy cập hoặc cuộc hội thoại không tồn tại.',
          });
          return;
        }
        attempt += 1;
        setWsStatus({ convId: activeId, state: 'reconnecting', error: '' });
        const delay = Math.min(1000 * 2 ** Math.min(attempt - 1, 4), 10000);
        reconnectTimerRef.current = window.setTimeout(connect, delay);
      };
    };

    const initTimer = window.setTimeout(connect, 0);

    return () => {
      disposed = true;
      window.clearTimeout(initTimer);
      if (reconnectTimerRef.current) {
        window.clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (wsRef.current) {
        const socket = wsRef.current;
        wsRef.current = null;
        socket.onopen = null;
        socket.onmessage = null;
        socket.onerror = null;
        socket.onclose = null;
        try {
          socket.close(1000, 'Component unmounted');
        } catch {
          // ignore
        }
      }
    };
  }, [activeId, refreshConversationsSilently, user?.id]);

  // Cuộn xuống tin nhắn mới nhất
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [currentMessages.length, activeId]);

  const handleSelectConversation = (convId) => {
    const idStr = String(convId);
    setManualSelectedId(idStr);
    setDraft('');
    navigate(`${baseChatPath}/${encodeURIComponent(idStr)}`, { replace: true });
  };

  const effectiveWsState = activeId
    ? wsStatus.convId === activeId
      ? wsStatus.state
      : 'connecting'
    : 'idle';
  const effectiveWsError = wsStatus.convId === activeId ? wsStatus.error : '';
  const msgLoading = loadingConvId === activeId;
  const msgError = activeId ? msgErrorsByConv[activeId] || '' : '';

  const handleSend = (event) => {
    event.preventDefault();
    const text = draft.trim();
    if (!text || !activeId || sending) return;

    const socket = wsRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      setWsStatus((prev) => ({
        ...prev,
        convId: activeId,
        error: 'Kết nối realtime chưa sẵn sàng. Vui lòng chờ kết nối lại rồi gửi.',
      }));
      return;
    }

    setSending(true);
    setWsStatus((prev) => ({ ...prev, convId: activeId, error: '' }));
    try {
      socket.send(
        JSON.stringify({
          event: 'message',
          message_type: 'TEXT',
          content: text,
          attachments: [],
        })
      );
      setDraft('');
    } catch {
      setWsStatus((prev) => ({
        ...prev,
        convId: activeId,
        error: 'Không thể gửi tin nhắn. Vui lòng thử lại.',
      }));
    } finally {
      setSending(false);
    }
  };

  const wsBadge = WS_STATE_META[effectiveWsState] || WS_STATE_META.idle;
  const counterpartName = activeConversation?.other_user?.full_name || 'Người dùng';
  const isCandidate = user?.role === 'CANDIDATE' || user?.user_type === 'CANDIDATE';

  return (
    <section className="card chat-two-col" aria-label="Tin nhắn trực tiếp">
      {/* Cột trái — 30%: Danh sách hội thoại */}
      <aside className="chat-sidebar" aria-label="Danh sách cuộc hội thoại">
        <div className="chat-sidebar-head">
          <h2 className="section-title">Hội thoại</h2>
          <span className="badge badge-gray">{conversations.length}</span>
        </div>

        <div className="chat-sidebar-search">
          <label className="mini-search">
            <Icon name="search" size={15} />
            <input
              type="search"
              placeholder="Tìm tên hoặc vị trí..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              aria-label="Tìm kiếm cuộc hội thoại"
            />
          </label>
        </div>

        {convError && (
          <div className="alert-box alert-error chat-inline-alert" role="alert">
            <span>{convError}</span>
            <button type="button" className="btn btn-secondary" onClick={handleRetryConversations}>
              Thử lại
            </button>
          </div>
        )}

        <div className="chat-conv-list">
          {convLoading ? (
            <div className="empty-state chat-empty-compact" role="status">
              Đang tải danh sách hội thoại…
            </div>
          ) : visibleConversations.length === 0 ? (
            <div className="empty-state chat-empty-compact">
              <Icon name="message" size={24} />
              <strong>
                {conversations.length ? 'Không tìm thấy hội thoại' : 'Chưa có cuộc hội thoại nào'}
              </strong>
              <p>
                {isCandidate
                  ? 'Khi nhà tuyển dụng liên hệ hoặc bạn trao đổi về đơn ứng tuyển, hội thoại sẽ hiển thị tại đây.'
                  : 'Mở danh sách ứng viên của tin tuyển dụng và bấm “Nhắn tin cho ứng viên” để bắt đầu.'}
              </p>
              <Link
                className="btn btn-secondary"
                to={isCandidate ? '/candidate/applications' : '/recruiter/jobs'}
              >
                {isCandidate ? 'Xem đơn ứng tuyển' : 'Tới tin tuyển dụng'}
              </Link>
            </div>
          ) : (
            visibleConversations.map((conv) => {
              const idStr = String(conv.id);
              const selected = idStr === activeId;
              const name = conv.other_user?.full_name || 'Đối tác tuyển dụng';
              return (
                <button
                  key={idStr}
                  type="button"
                  className={`chat-conv-item ${selected ? 'active' : ''}`}
                  aria-current={selected ? 'true' : undefined}
                  onClick={() => handleSelectConversation(idStr)}
                >
                  <span className="avatar avatar-blue">{initials(name)}</span>
                  <span className="chat-conv-body">
                    <span className="chat-conv-top">
                      <strong>{name}</strong>
                      <small>{formatShortTime(conv.updated_at)}</small>
                    </span>
                    {conv.job_title && <span className="chat-conv-job">{conv.job_title}</span>}
                    <span className="chat-conv-bottom">
                      <span className="chat-conv-last">
                        {conv.last_message || 'Chưa có tin nhắn nào'}
                      </span>
                      {conv.unread_count > 0 && (
                        <b className="chat-unread-pill">{conv.unread_count}</b>
                      )}
                    </span>
                  </span>
                </button>
              );
            })
          )}
        </div>
      </aside>

      {/* Cột phải — 70%: Lịch sử tin nhắn & khung soạn thảo */}
      <div className="chat-main">
        {!activeId ? (
          <div className="empty-state chat-main-empty">
            <Icon name="message" size={30} />
            <strong>Chọn một cuộc hội thoại để bắt đầu</strong>
            <p>Chọn cuộc hội thoại ở cột bên trái để xem lịch sử và trao đổi trực tiếp.</p>
          </div>
        ) : (
          <>
            <header className="chat-main-head">
              <div className="chat-main-peer">
                <span className="avatar avatar-blue">{initials(counterpartName)}</span>
                <div>
                  <strong>{counterpartName}</strong>
                  <span>
                    {activeConversation?.job_title
                      ? `Vị trí: ${activeConversation.job_title}`
                      : `Mã hội thoại: ${activeId}`}
                  </span>
                </div>
              </div>
              <span className={`badge ${wsBadge.tone}`} role="status">
                {wsBadge.label}
              </span>
            </header>

            {(msgError || effectiveWsError) && (
              <div className="alert-box alert-error chat-banner-error" role="alert">
                {msgError || effectiveWsError}
              </div>
            )}

            <div className="chat-messages-pane" role="log" aria-live="polite">
              {msgLoading && currentMessages.length === 0 ? (
                <div className="empty-state chat-empty-compact" role="status">
                  Đang tải lịch sử tin nhắn…
                </div>
              ) : currentMessages.length === 0 ? (
                <div className="empty-state chat-empty-compact">
                  <Icon name="spark" size={24} />
                  <strong>Bắt đầu cuộc trò chuyện</strong>
                  <p>Hãy gửi lời chào đầu tiên tới {counterpartName}.</p>
                </div>
              ) : (
                currentMessages.map((msg) => {
                  const isMine = String(msg.sender_id) === String(user?.id);
                  return (
                    <div
                      key={String(msg.id)}
                      className={`chat-bubble-row ${isMine ? 'mine' : 'theirs'}`}
                    >
                      {!isMine && (
                        <span className="avatar avatar-small avatar-blue" aria-hidden="true">
                          {initials(counterpartName)}
                        </span>
                      )}
                      <div className="chat-bubble">
                        {msg.content && <p>{msg.content}</p>}
                        {Array.isArray(msg.attachments) &&
                          msg.attachments.map((url) => (
                            <a
                              key={url}
                              href={url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="chat-attachment-link"
                            >
                              <Icon name="file" size={14} /> Tệp đính kèm
                            </a>
                          ))}
                        <span className="chat-bubble-time">{formatMessageTime(msg.created_at)}</span>
                      </div>
                    </div>
                  );
                })
              )}
              <div ref={bottomRef} />
            </div>

            <form className="chat-composer" onSubmit={handleSend}>
              <input
                type="text"
                className="input chat-composer-input"
                aria-label="Nội dung tin nhắn"
                placeholder={
                  effectiveWsState === 'connected'
                    ? 'Nhập tin nhắn và nhấn Enter để gửi...'
                    : 'Đang kết nối tới máy chủ chat...'
                }
                maxLength={2000}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                disabled={effectiveWsState === 'closed'}
              />
              <button
                type="submit"
                className="btn btn-primary chat-send-btn"
                disabled={!draft.trim() || sending || effectiveWsState !== 'connected'}
              >
                <Icon name="send" size={16} />
                <span>{sending ? 'Đang gửi...' : 'Gửi'}</span>
              </button>
            </form>
          </>
        )}
      </div>
    </section>
  );
}
