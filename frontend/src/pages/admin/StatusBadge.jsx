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
  const [label, color] = STATUS[value] || [value, 'gray'];
  return <span className={`badge badge-${color}`}>{label}</span>;
}

