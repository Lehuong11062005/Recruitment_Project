const STATUS = {
  ACTIVE: ['Hoạt động', 'green'],
  BANNED: ['Đã khóa', 'red'],
  PENDING: ['Chờ duyệt', 'amber'],
  VERIFIED: ['Đã duyệt', 'green'],
  REJECTED: ['Từ chối', 'red'],
  OPEN: ['Đang tuyển', 'green'],
  CLOSED: ['Đã đóng', 'gray'],
  HIDDEN: ['Đã ẩn', 'amber'],
};

export default function StatusBadge({ value }) {
  const normalized = typeof value === 'string' ? value.trim() : value;
  const [label, color] = STATUS[normalized] || [normalized, 'gray'];
  return <span className={`badge badge-${color}`}>{label}</span>;
}

