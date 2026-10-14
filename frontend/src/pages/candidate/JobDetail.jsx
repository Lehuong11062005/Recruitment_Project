import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';

export default function JobDetail() {
  const { jobId } = useParams();
  const [selectedFile, setSelectedFile] = useState(null);
  const [statusMsg, setStatusMsg] = useState('');

  const handleApply = (e) => {
    e.preventDefault();
    setStatusMsg('Đã gửi yêu cầu ứng tuyển (UC-C5). Kết quả AI Matching sẽ được cập nhật.');
  };

  return (
    <div>
      <div style={{ marginBottom: '16px' }}>
        <Link to="/candidate/jobs" style={{ fontSize: '14px', color: '#155EEF' }}>
          ← Quay lại danh sách việc làm
        </Link>
      </div>

      <div
        style={{
          backgroundColor: '#FFFFFF',
          border: '1px solid #DCE5F0',
          borderRadius: '12px',
          padding: '24px',
        }}
      >
        <h1 style={{ fontSize: '22px', fontWeight: 700, color: '#142B4A', marginBottom: '8px' }}>
          Chi tiết tin tuyển dụng #{jobId} (UC-C5 & UC-C6)
        </h1>
        <p style={{ fontSize: '14px', color: '#64748B', marginBottom: '20px' }}>
          Tải lên CV định dạng PDF (tối đa 5MB) để nộp đơn ứng tuyển hoặc xem điểm độ phù hợp AI.
        </p>

        {statusMsg && <div className="alert-box alert-success">{statusMsg}</div>}

        <form onSubmit={handleApply}>
          <div className="form-group">
            <label className="form-label">Chọn file CV (PDF)</label>
            <input
              type="file"
              accept=".pdf,application/pdf"
              onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
              className="form-input"
              style={{ paddingTop: '8px' }}
            />
          </div>
          <button type="submit" className="btn-primary" style={{ maxWidth: '220px' }}>
            Gửi hồ sơ ứng tuyển
          </button>
        </form>
      </div>
    </div>
  );
}