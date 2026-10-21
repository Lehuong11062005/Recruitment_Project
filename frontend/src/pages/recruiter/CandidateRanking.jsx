import { Link, useParams } from 'react-router-dom';
import Icon from '../../components/Icon';

export default function CandidateRanking() {
  const { jobId } = useParams();

  return (
    <div className="content-stack">
      <section className="card api-unavailable">
        <span className="badge badge-amber">CHƯA XÁC MINH API</span>
        <h2 className="section-title">Xếp hạng và đánh giá ứng viên</h2>
        <p>
          Core Service chưa cung cấp API để liệt kê hồ sơ ứng tuyển theo tin hoặc cập nhật pipeline.
          Không có ứng viên, điểm AI hay trạng thái mẫu được hiển thị.
        </p>
        <p className="small">Mã tin tuyển dụng: {jobId}</p>
        <Link className="btn btn-secondary" to="/recruiter/jobs">
          <Icon name="chevron" size={15} /> Quay lại tin tuyển dụng
        </Link>
      </section>
    </div>
  );
}
