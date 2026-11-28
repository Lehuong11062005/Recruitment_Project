# THIẾT KẾ KIẾN TRÚC CHI TIẾT (PHASE 1)
## Configurable AI Matching Weights theo từng Tin tuyển dụng (`v2.0-configurable`)

- **Ngày xác lập:** 27/11/2026
- **Trạng thái:** Đã xác nhận trước khi triển khai mã nguồn Phase 2.

---

## 1. Thiết Kế Cơ Sở Dữ Liệu (Database Schema — MongoDB)

### 1.1. Collection `job_postings`
Bổ sung sub-document `matching_weights` lưu độc lập trên từng bản ghi `JobPosting`:

```json
{
  "_id": "ObjectId(...)",
  "title": "Backend Python Developer",
  "matching_weights": {
    "skill_weight": 0.6,
    "semantic_weight": 0.25,
    "experience_weight": 0.15
  }
}
```

**Quy tắc ràng buộc dữ liệu (`MatchingWeights`):**
- Cả 3 trường `skill_weight`, `semantic_weight`, `experience_weight` bắt buộc có mặt khi truyền object `matching_weights` (`extra="forbid"`).
- Kiểu dữ liệu: số thực hữu hạn (`int | float`, loại trừ `bool`, `NaN`, `Infinity`).
- Miền giá trị từng trọng số: `0.0 <= w <= 1.0` (từ chối số âm và giá trị `> 1.0`).
- Ràng buộc tổng trọng số: `abs((skill_weight + semantic_weight + experience_weight) - 1.0) <= 1e-4` (xử lý sai số dấu phẩy động IEEE-754 như `0.1 + 0.2 + 0.7`, đồng thời từ chối nghiêm ngặt tổng `= 0`, `< 0.9999` hoặc `> 1.0001`). Chuẩn hóa lưu `round(float(w), 4)`.
- Giá trị mặc định khi không truyền `matching_weights`:
  - `skill_weight = 0.50`
  - `semantic_weight = 0.35`
  - `experience_weight = 0.15`

### 1.2. Collection `applications` (Application Snapshot)
Lưu bất biến bộ trọng số đã dùng tại đúng thời điểm chấm điểm hồ sơ ứng tuyển:

```json
{
  "_id": "ObjectId(...)",
  "job_id": "ObjectId(...)",
  "candidate_id": "ObjectId(...)",
  "ai_match_score": 86.0,
  "matching_version": "v2.0-configurable",
  "matching_weights_snapshot": {
    "skill_weight": 0.6,
    "semantic_weight": 0.25,
    "experience_weight": 0.15
  },
  "ai_analysis": {
    "matched": ["ObjectId(...)"],
    "missing": ["ObjectId(...)"],
    "score_breakdown": {
      "skill_score": 90.0,
      "semantic_score": 80.0,
      "experience_score": 80.0,
      "skill_match": 90.0,
      "semantic_match": 80.0,
      "experience_match": 80.0
    },
    "recommendation": "..."
  }
}
```

**Nguyên tắc bất biến (Snapshot Immutability):**
- Khi Recruiter chỉnh sửa `job_postings.matching_weights`, hệ thống **không tính lại** và **không ghi đè** `ai_match_score`, `score_breakdown`, `matching_weights_snapshot` hay `matching_version` của các `applications` đã nộp trước đó.
- Chỉ khi có đơn ứng tuyển mới (`POST /api/v1/applications`) hoặc khi phân tích lại một đơn đang ở trạng thái `FAILED` (`POST /api/v1/ai-analysis/{id}/retry`), hệ thống mới đọc `job.matching_weights` hiện hành và lưu snapshot tương ứng.

---

## 2. Hợp Đồng API (API Contract) & Phân Quyền

### 2.1. Core Service (`Port 8001` — qua Gateway `Port 8000`)
1. **Tạo tin tuyển dụng (`POST /api/v1/jobs` & `POST /api/v1/jobs/managed`):**
   - Quyền: `RECRUITER` (đã liên kết `company_id`). Candidate/Guest bị từ chối `403`/`401`.
   - Request body: `JobCreateSchema` có thêm `matching_weights: Optional[MatchingWeightsSchema] = None` (nếu `None` hoặc không gửi → gán mặc định `{0.50, 0.35, 0.15}`; nếu gửi sai → trả `422 Unprocessable Entity`).
   - Response: Trả về thông tin tin tuyển dụng có đầy đủ `matching_weights`.
2. **Chỉnh sửa tin tuyển dụng (`PUT /api/v1/jobs/{job_id}`, `PATCH /api/v1/jobs/{job_id}`, `PUT /api/v1/jobs/managed/{job_id}`):**
   - Quyền: `RECRUITER` sở hữu tin (`job.recruiter_id == current_user.id`; HR khác bị từ chối `403`).
   - Request body: `JobUpdateSchema` có `matching_weights: Optional[MatchingWeightsSchema] = None`. Nếu không gửi trường `matching_weights` (`exclude_unset=True`), giữ nguyên trọng số cũ của tin; nếu gửi `null` hoặc trọng số sai ràng buộc → trả `422`.
   - Response: Trả về tin tuyển dụng đã cập nhật kèm `matching_weights`.
3. **Lấy thông tin tin tuyển dụng (`GET /api/v1/jobs/my-jobs`, `GET /api/v1/jobs/managed/{job_id}`, `GET /api/v1/jobs/{job_id}`, `GET /api/v1/jobs`):**
   - Trả về trường `matching_weights` trong mọi response (nếu document cũ trong DB chưa có trường này thì trả default `{0.50, 0.35, 0.15}`).
   - Endpoint mới `GET /api/v1/jobs/managed/{job_id}` cho phép Recruiter chủ tin lấy chi tiết tin của mình (kể cả khi `CLOSED`/`HIDDEN` hoặc công ty `PENDING`).
4. **Chấm điểm & Xem kết quả ứng tuyển (`POST /api/v1/applications`, `POST /api/v1/ai-analysis/preview`, `POST /api/v1/ai-analysis/{id}/retry`, `GET /api/v1/jobs/{job_id}/applications`, `GET /api/v1/applications/me`, `GET /api/v1/applications/{id}`, `GET /api/v1/applications/{id}/ai-analysis`):**
   - **Bảo mật:** Client/Candidate tuyệt đối không có quyền truyền trọng số vào API nộp đơn hay xem trước; Core Service tự truy xuất `resolve_matching_weights(job)` từ MongoDB để gửi sang AI Service.
   - Response bổ sung: `matching_weights_snapshot` (`Optional[MatchingWeightsSchema]`), `score_breakdown` (`Optional[Dict[str, float]]` ở mức ngoài cùng đồng thời giữ nguyên trong `ai_analysis.score_breakdown`), và `matching_version`.

### 2.2. AI Service (`Port 8002`)
1. **`POST /api/v1/ai/match`:**
   - Request (`MatchingRequest`):
     ```json
     {
       "cv_text": "...",
       "jd_text": "...",
       "candidate_skills": ["Python", "FastAPI"],
       "required_skills": ["Python", "FastAPI", "Docker"],
       "candidate_experience_years": 3.0,
       "job_experience_required": 2.0,
       "matching_weights": {
         "skill_weight": 0.6,
         "semantic_weight": 0.25,
         "experience_weight": 0.15
       }
     }
     ```
     *(Hỗ trợ cả alias đầu vào `weights` cho unit test độc lập; nếu không truyền `matching_weights` thì dùng default `{0.50, 0.35, 0.15}`; nếu truyền trọng số không hợp lệ thì Pydantic từ chối ngay với `HTTP 422` trước khi chạy mô hình).*
   - Response (`MatchingResponse`):
     - `ai_match_score: float`
     - `matching_version: "v2.0-configurable"`
     - `score_breakdown: Dict[str, float]`
     - `matching_weights_snapshot: MatchingWeights`
     - `embedding_vector: List[float]`
     - `ai_analysis: AIAnalysisBreakdown`
2. **`POST /api/v1/ai/match-cv`:**
   - Nhận thêm form field tùy chọn `matching_weights` (chuỗi JSON), xác thực nghiêm ngặt qua `MatchingWeights` trước khi chấm điểm (`HTTP 422` nếu sai).

---

## 3. Công Thức AI Matching Chuẩn Hóa

Giữ nguyên 100% logic trích xuất kỹ năng (`CVParserService`), mô hình `paraphrase-multilingual-MiniLM-L12-v2` và cách tính 3 điểm thành phần `skill_score`, `semantic_score`, `experience_score` thuộc `[0.0, 100.0]`:

$$\text{ai\_match\_score} = \text{round}\left(w_{\text{skill}} \cdot S_{\text{skill}} + w_{\text{semantic}} \cdot S_{\text{semantic}} + w_{\text{experience}} \cdot S_{\text{experience}},\ 1\right)$$

- Với bộ trọng số mặc định $(0.50,\ 0.35,\ 0.15)$, kết quả số học trùng khớp tuyệt đối 100% với công thức cũ.
- Lưu ý kiểm tra toán học cho bộ điểm mẫu $(S_{\text{skill}}=90,\ S_{\text{semantic}}=80,\ S_{\text{experience}}=80)$:
  - Với $(0.60,\ 0.25,\ 0.15)$: $90 \times 0.60 + 80 \times 0.25 + 80 \times 0.15 = 54 + 20 + 12 = 86.0$.
  - Với mặc định $(0.50,\ 0.35,\ 0.15)$: $90 \times 0.50 + 80 \times 0.35 + 80 \times 0.15 = 45 + 28 + 12 = 85.0$ *(còn nếu $S_{\text{skill}}=89, S_{\text{semantic}}=80, S_{\text{experience}}=80$ thì $89 \times 0.50 + 80 \times 0.35 + 80 \times 0.15 = 84.5$; cả hai trường hợp đều sẽ được kiểm chứng tường minh trong Unit Test Phase 4)*.
  - Với $(1.00,\ 0.00,\ 0.00)$: $90 \times 1.00 + 80 \times 0.00 + 80 \times 0.00 = 90.0$.

---

## 4. Chiến Lược Tương Thích Ngược (Backward Compatibility Strategy)

1. **Đối với 9 `job_postings` hiện hữu trong `recruitment_db`:**
   - Trong Beanie `JobPosting`, khai báo `matching_weights: Optional[MatchingWeights] = Field(default_factory=MatchingWeights)`.
   - Mọi luồng đọc/serialize (`serialize_job`, `_serialize_candidate_job`, `resolve_matching_weights(job)`) đều kiểm tra `getattr(job, "matching_weights", None)` — nếu `None` hoặc thiếu khóa trong document thô của MongoDB thì trả về `{skill_weight: 0.5, semantic_weight: 0.35, experience_weight: 0.15}`. Không cần migration ghi đè dữ liệu gốc.
2. **Đối với 3 `applications` hiện hữu trong `recruitment_db`:**
   - Trường `matching_weights_snapshot` là `Optional[MatchingWeights] = None`. Các đơn cũ (`v1.0-SBERT`) giữ nguyên `matching_weights_snapshot = null`, `ai_status` và `score_breakdown` gốc (`skill_match`, `semantic_match`, `experience_match`).
   - Giao diện Frontend đọc an toàn cả `*_score` lẫn `*_match`; khi `matching_weights_snapshot` có mặt sẽ hiển thị chi tiết `điểm × % trọng số`, còn với bản ghi cũ chưa có snapshot vẫn hiển thị đầy đủ điểm thành phần và ghi chú phiên bản cũ mà không lỗi giao diện.
3. **Đối với các bài test hiện có:**
   - Toàn bộ 30 bài test Core Service, 4 bài test API Gateway và 5 bài test AI Service giữ nguyên khả năng tương thích 100% nhờ cơ chế optional/default fallback.
