# BÁO CÁO NGHIỆM THU CUỐI CÙNG (FINAL AUDIT) — TUẦN 10 & TUẦN 11
## Smart Recruitment Platform (`Recruitment_Project`)

- **Ngày thực hiện:** 26/11/2026
- **Nhánh làm việc:** `main` (đối chiếu trực tiếp với `origin/main` tại commit `c680bca` — **chưa tự ý commit, merge hay push**)
- **Môi trường kiểm thử thực tế:** Windows, Python 3.13.9, React 19 + Vite 8.3.0, MongoDB 8.2 (`localhost:27017`), API Gateway (`:8000`), Core Service (`:8001`), Frontend (`:5173`)

---

## 1. Bảng Nghiệm Thu Từng Task Theo Phân Công Thành Viên

> Quy ước trạng thái:
> - **PASS**: Đã hoàn thiện đầy đủ tính năng và có bằng chứng kiểm thử thực thi thành công (Automated + Live Integration/Browser E2E).
> - **PARTIAL**: Đã có code nhưng chưa đủ chức năng hoặc thiếu bằng chứng thực thi.
> - **FAIL**: Chưa triển khai hoặc kiểm thử thất bại.
> - **BLOCKED**: Không thể kiểm chứng do phụ thuộc hệ thống bên ngoài.

| Thành viên | Task / Use Case | Hạng mục nghiệm thu | Trạng thái ban đầu (khi pull `main`) | Trạng thái cuối cùng (Final Audit) | Bằng chứng thực thi thực tế |
|---|---|---|---|---|---|
| **Mạnh** | **Task 9.1 (UC-R6)** | Pipeline tuyển dụng Backend (`PATCH /api/v1/applications/{id}/status`) & `status_history` | PARTIAL | **PASS** | `pytest` (`test_task_9_1_and_9_3...`) + Live E2E Flows 1 & 2 qua Gateway `:8000` |
| **Mạnh** | **Task 9.1 (UC-R6)** | Pipeline tuyển dụng Frontend (`CandidateRanking.jsx`) + Modal lịch phỏng vấn + Hiển thị `status_history` | PARTIAL | **PASS** | `eslint` (0 lỗi), `vite build` (386ms) + Browser E2E trên `:5173` |
| **Mạnh** | **Task 9.1 (UC-R7)** | Khởi tạo Chat từ HR (`POST /api/v1/conversations` + điều hướng `/recruiter/chat/{id}`) | PARTIAL | **PASS** | Live E2E Flow 3 + Browser E2E xác nhận idempotent & điều hướng đúng hội thoại |
| **Cường** | **Task 9.3** | Notification Backend (`GET /api/v1/notifications`, `PATCH /api/v1/notifications/{id}/read`) + UI Chuông thông báo | PARTIAL | **PASS** | `pytest` + Live E2E Flows 1 & 2 + Browser E2E kiểm tra badge chưa đọc & điều hướng |
| **Cường** | **Task 9.3** | Email Service (`BackgroundTasks` + `SMTP_*` env + chống gửi trùng + chịu lỗi) | PARTIAL | **PASS** | `test_task_9_3_smtp_loopback_and_failure_resilience` (Loopback TCP SMTP Server thật) *(gửi ra Internet thật chờ điền tài khoản `SMTP_*` khi deploy)* |
| **Cường** | **Task 10.3** | Chat REST API (`POST /conversations`, `GET /conversations`, `GET /conversations/{id}/messages`) + Unique Index | PARTIAL | **PASS** | `test_task_10_3_chat_rest_and_realtime_websocket` + kiểm tra index `unique_job_candidate_conversation` trên MongoDB |
| **Cường** | **Task 10.3** | Chat WebSocket Core Service (`ws://localhost:8001/ws/chat/{id}?token={jwt}`) | PARTIAL | **PASS** | Đã sửa race condition `accept()`; Uvicorn thật + 2 client `websockets` gửi/nhận đồng thời PASS |
| **Hùng** | **Task 9.2 (UC-C7)** | Theo dõi đơn ứng tuyển Backend (`GET /api/v1/applications/me` & `/applications/{id}`) | PARTIAL | **PASS** | `test_task_9_2...` + kiểm tra đọc 3 đơn thực tế trong `recruitment_db` |
| **Hùng** | **Task 9.2 (UC-C7)** | Theo dõi đơn ứng tuyển Frontend (`MyApplications.jsx` & `ApplicationDetail.jsx`) | FAIL | **PASS** | Đã triển khai thanh tiến trình 4 bước (phân biệt rõ `HIRED` xanh vs `REJECTED` đỏ), thẻ lịch phỏng vấn, lịch sử trạng thái; Browser E2E PASS |
| **Hùng** | **Task 10.3 (UC-C8)** | Frontend Chat Realtime (`ChatPage.jsx` 2 cột 30%/70% dùng chung Candidate & Recruiter) | FAIL | **PASS** | Đã thay thế placeholder bằng `ChatPage.jsx` kết nối qua Gateway `:8000`, Browser E2E xác nhận gửi/nhận & reload giữ nguyên lịch sử |
| **Nam** | **Task 10.1 (UC-A1..A3)** | Admin Moderation APIs (`users`, `companies`, `jobs`, xóa mềm `deleted_at`, chặn tự khóa `409`) | PARTIAL | **PASS** | `test_admin_moderation.py` (7/7 PASS) + `test_task_10_1...` trên MongoDB thật + Live E2E Flow 5 |
| **Nam** | **Task 10.2** | Frontend Admin Portal (`Dashboard`, `ManageUsers`, `ApproveCompanies`, `ModerateJobs`, Layout) | PARTIAL | **PASS** | Đã khắc phục lỗi double-sidebar gap (`gapAfterSidebar = 0px` tại `1366×768`, `1570×920`, `1920×1080`) + Browser E2E cả 4 trang PASS |
| **Hưởng** | **Task 10.1 (UC-A4)** | Admin Statistics API (`GET /api/v1/admin/statistics`) | PARTIAL | **PASS** | Đối chiếu khớp 100% truy vấn thủ công `recruitment_db` (kể cả chuẩn hóa bản ghi cũ `"CLOSED "`) + test DB rỗng PASS |
| **Hưởng** | **Task Tuần 11** | API Gateway WebSocket Proxy (`ws://localhost:8000/ws/chat/{id}` → `:8001`) | PARTIAL | **PASS** | Đã sửa race condition handshake upstream; `test_ws_proxy.py` (4/4 PASS) + Live 2-client WS qua `:8000` PASS |

---

## 2. Kiểm Toán Chi Tiết 8 Chiều Cho Từng Nhóm Chức Năng

### 2.1. Phân công của MẠNH — Pipeline Tuyển Dụng & Khởi Tạo Chat (UC-R6, UC-R7)
1. **Code Backend:** `services/core-service/app/routers/applications.py`, `app/schemas/application.py`, `app/services/application_service.py`. Chỉ chấp nhận 5 giá trị `Literal["APPLIED", "SCREENING", "INTERVIEW", "HIRED", "REJECTED"]`. Bắt buộc nhập `interview_schedule` (`time` + `location` hoặc `link`) khi chuyển sang `INTERVIEW`. Nối thêm (`append`) `{ status, changed_by, time }` vào `status_history` mà không ghi đè lịch sử cũ; `StatusHistoryItem.time` xuất chuẩn ISO UTC (`...Z`).
2. **Code Frontend:** `frontend/src/pages/recruiter/CandidateRanking.jsx` hiển thị trạng thái hiện tại, dropdown đổi trạng thái, modal nhập lịch phỏng vấn khi chọn `INTERVIEW`, ô `recruiter_note`, trạng thái loading/alert, danh sách `Lịch sử thay đổi trạng thái`, và nút `"Nhắn tin cho ứng viên"`.
3. **API Contract Frontend ↔ Backend:**
   - `PATCH /api/v1/applications/{id}/status` nhận `{ pipeline_status, recruiter_note?, interview_schedule?: { time, location, link } }` → trả `ApplicationStatusResponse` (`id`, `pipeline_status`, `recruiter_note`, `interview_schedule`, `status_history`, `updated_at`), khớp tuyệt đối với `useApplicationReview` ở Frontend.
   - Nút `"Nhắn tin cho ứng viên"` gọi `POST /api/v1/conversations` với `{ job_id, candidate_id }` → nhận `ConversationResponse.id` và điều hướng `/recruiter/chat/{id}`.
4. **Quyền truy cập & JWT:** Yêu cầu `Depends(get_current_recruiter)` và kiểm tra `job.recruiter_id == user.id` (cùng kiểm tra `company_id`). Candidate, Admin, HR công ty khác và HR đồng nghiệp không đứng tên tin đều bị từ chối `403`.
5. **Dữ liệu MongoDB thực tế:** Index `unique_job_candidate_application` và `job_id_1_ai_match_score_-1` hoạt động đúng; `status_history` trong 3 bản ghi thực tế của `recruitment_db` đều có cấu trúc `{ status, changed_by, time }` đồng nhất.
6. **Test chức năng & 7. Integration Test:** `test_task_9_1_and_9_3_pipeline_permissions_history_interview_and_notifications` **PASSED**; Live E2E Flows 1, 2, 3 và Browser E2E **PASSED**.
8. **Bổ sung đã thực hiện:** Chống ghi trùng `status_history`/notification khi gửi lại cùng lịch phỏng vấn, chuẩn hóa múi giờ `UTCDatetime` cho `status_history.time`, và hiển thị `status_history` trên giao diện HR.

---

### 2.2. Phân công của HÙNG — Candidate Application Tracking & Frontend Chat (UC-C7, UC-C8)
1. **Code Backend (`GET /api/v1/applications/me` & `GET /api/v1/applications/{id}`):** Trả về danh sách đơn của chính ứng viên đang đăng nhập (kèm phân trang `skip`, `limit`), gom truy vấn `$in` cho `job_postings` và `companies`, gắn cờ `is_deleted` khi job/công ty đã xóa mềm, kèm đầy đủ `pipeline_status`, `status_history`, `interview_schedule`.
2. **Code Frontend:**
   - `MyApplications.jsx` & `ApplicationDetail.jsx` sử dụng component `PipelineProgress.jsx` hiển thị 4 bước (`Đã nộp` → `Đang sơ loại` → `Hẹn phỏng vấn` → `Kết quả`), phân biệt rõ màu xanh lá thành công (`Kết quả: Trúng tuyển`) khi `HIRED` và màu đỏ từ chối (`Kết quả: Từ chối`) khi `REJECTED`, kèm thẻ `Lịch phỏng vấn` và timeline `Lịch sử thay đổi trạng thái`.
   - `ChatPage.jsx` bố cục 2 cột chuẩn 30% (danh sách hội thoại, tìm kiếm, `last_message`, `updated_at`, số chưa đọc) và 70% (lịch sử tin nhắn, badge trạng thái kết nối realtime, ô nhập và nút gửi), dùng chung cho `/candidate/chat` và `/recruiter/chat` (tương thích ngược với `/messages`).
3. **API Contract Frontend ↔ Backend:**
   - `ApplicationDetail.jsx` gọi `GET /api/v1/applications/{id}` (đã sửa lỗi cũ gọi nhầm endpoint AI).
   - `ChatPage.jsx` gọi `GET /api/v1/conversations`, `GET /api/v1/conversations/{id}/messages` và kết nối `ws://localhost:8000/ws/chat/{id}?token=...`, khử trùng theo `msg.id` và lọc nghiêm ngặt theo `msg.conversation_id === activeId`.
4. **Quyền truy cập & JWT:** Ứng viên chỉ xem được đơn của mình (`app.candidate_id == user.id`, đơn người khác trả `404`); `recruiter_note` không tồn tại trong `ApplicationResponse` và luôn là `None` với ứng viên ở `ApplicationDetailResponse`; JWT không bao giờ xuất hiện trên thanh URL của trình duyệt hay `console.log`.
5. **Dữ liệu MongoDB thực tế:** Đã chạy `verify_readonly_real_db.py` đọc trực tiếp cả 3 đơn thực tế của tài khoản `user@gmail.com` trong `recruitment_db` (bao gồm các đơn cũ có `ai_status: None` và `matching_version: "v1.0-SBERT"`) → trả `200 OK` không lỗi schema.
6. **Test chức năng & 7. Integration Test:** `test_task_9_2_candidate_applications_isolation_and_soft_deleted_job` **PASSED**; Live E2E Flows 1, 2, 4 và Browser E2E (kể cả reload trang chat) **PASSED**.

---

### 2.3. Phân công của CƯỜNG — Notifications, Email & Chat Backend (Task 9.3, Task 10.3)
1. **Code Backend:**
   - `notifications.py` & `notification_service.py`: Lưu vào collection `notifications` với `type = "APPLICATION_STATUS"`, `GET /api/v1/notifications` sắp xếp `[("created_at", -1), ("_id", -1)]`, `PATCH /api/v1/notifications/{id}/read` cập nhật `is_read = True`.
   - `email_service.py`: Đọc cấu hình từ biến môi trường (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_USE_TLS`), chạy nền qua `FastAPI BackgroundTasks`, bọc ngoại lệ đầy đủ để lỗi SMTP không bao giờ làm hỏng thao tác lưu trạng thái đơn.
   - `chat.py` & `chat_service.py`: Sử dụng đúng 2 collection `conversations` và `messages` (không tạo collection thừa), lưu tin nhắn vào MongoDB đồng thời cập nhật `conversations.last_message` & `updated_at` rồi broadcast tới mọi kết nối trong phòng.
2. **Code Frontend liên quan:** `NotificationBell.jsx` trên Topbar đồng bộ danh sách thông báo chưa đọc và điều hướng tới `action_url` (`/candidate/applications/{id}`).
3. **API Contract & 4. Quyền truy cập / JWT:**
   - Thông báo của user khác trả `404` khi gọi `PATCH /read` và không bao giờ xuất hiện trong `GET /notifications`.
   - REST Chat chặn `403` khi HR không sở hữu job, ứng viên chưa nộp đơn vào job (hoặc ứng viên chưa nộp đơn cố mở chat trên job đã đóng/ẩn), hoặc ứng viên truyền `candidate_id` của người khác.
   - WebSocket kiểm tra JWT và tư cách thành viên phòng **trước khi** hoàn tất đăng ký nhận broadcast; trả mã đóng `4401` (JWT sai/hết hạn) và `4404` (ngoài cuộc hội thoại / phòng không tồn tại).
5. **Dữ liệu MongoDB thực tế:** Đã xác minh các index thực tế trên MongoDB:
   - `notifications`: `['_id_', 'user_id_1_is_read_1', 'expire_at_1']`
   - `conversations`: `['_id_', 'candidate_id_1', 'recruiter_id_1', 'unique_job_candidate_conversation']`
   - `messages`: `['_id_', 'conversation_id_1_created_at_-1']`
6. **Test chức năng & 7. Integration Test:**
   - `test_task_9_3_smtp_loopback_and_failure_resilience` (dựng TCP SMTP Server cục bộ xác nhận nhận đúng bản tin MIME HTML/Text và chịu lỗi khi sập cổng): **PASSED**.
   - `test_task_10_3_chat_rest_and_realtime_websocket` (Uvicorn thật + 2 client `websockets` đồng thời): **PASSED**.
8. **Bổ sung đã thực hiện:** Khắc phục lỗi race condition `websocket.accept()` sớm trong `chat.py`, thêm unique index `(job_id, candidate_id)` cho `conversations`, và bổ sung `NotificationBell.jsx` trên Frontend.

---

### 2.4. Phân công của NAM — Admin Moderation APIs & Frontend Admin Portal (UC-A1..A3, Task 10.2)
1. **Code Backend (`routers/admin.py`, `schemas/admin.py`):**
   - Toàn bộ router gắn `dependencies=[Depends(get_current_admin)]` (`current_user.role == "ADMIN"`).
   - UC-A1 (`GET /admin/users`, `PATCH /admin/users/{id}/status`): Lọc `role`, `user_type`, `status`, tìm kiếm `q` (tên/email), chuyển `ACTIVE`/`BANNED`, chặn Admin tự khóa tài khoản đang đăng nhập (`409 Conflict`).
   - UC-A2 (`GET /admin/companies`, `PATCH /admin/companies/{id}/verify`): Lọc `PENDING`/`VERIFIED`/`REJECTED`, tìm kiếm `q`, duyệt `VERIFIED` hoặc `REJECTED`.
   - UC-A3 (`GET /admin/jobs`, `PATCH /admin/jobs/{id}/status`): Lọc `OPEN`/`CLOSED`/`HIDDEN`, tìm kiếm `q`, ẩn tin (`HIDDEN`) hoặc xóa mềm (`DELETED` → gán `deleted_at`), không xóa vật lý và không làm mất `applications` liên quan.
2. **Code Frontend (`Dashboard.jsx`, `ManageUsers.jsx`, `ApproveCompanies.jsx`, `ModerateJobs.jsx`, `AdminList.jsx`, `AdminLayout.jsx`, `StatusBadge.jsx`):**
   - Tuân thủ nghiêm ngặt Design System (`#155EEF`, `#142B4A`, `#F5F8FC`, `#DCE5F0`, `#EEF4FF`, `#64748B`, font Inter, bo góc 8px/12px, không gradient), bố cục chuẩn `Sidebar (264px) | Main Content (gap = 0px)` trên mọi độ phân giải desktop.
3. **API Contract & 4. Quyền truy cập / JWT:** Mọi thao tác trên UI gọi API thật qua `adminService.js`; Candidate và Recruiter gọi trực tiếp backend đều bị chặn `403`, không có token bị chặn `401`; user bị `BANNED` lập tức bị chặn `403` ở `get_current_user`.
5. **Dữ liệu MongoDB thực tế:** Đã kiểm tra trực tiếp trên 13 users, 5 companies, 9 jobs trong `recruitment_db`, xử lý chuẩn cả bản ghi cũ có khoảng trắng dư (`status: "CLOSED "`).
6. **Test chức năng & 7. Integration Test:** `test_admin_moderation.py` (`7/7 PASSED`), `test_task_10_1_admin_moderation_and_statistics_with_real_mongodb` (**PASSED**), Live E2E Flow 5 và Browser E2E cả 4 trang Admin (**PASSED**).

---

### 2.5. Phân công của HƯỞNG — Admin Statistics & API Gateway WebSocket Proxy (UC-A4, Task Tuần 11)
1. **Admin Statistics (`GET /api/v1/admin/statistics` — `services/admin_service.py`):**
   - Bảo vệ bởi `get_current_admin` (`ADMIN` duy nhất).
   - Truy vấn trực tiếp MongoDB (không hardcode, không gọi sai là AI Accuracy): tổng `CANDIDATE`/`RECRUITER`/`ADMIN`, công ty `PENDING`/`VERIFIED`/`REJECTED`, tin `OPEN`/`CLOSED`/`HIDDEN`, đơn theo 5 `pipeline_status`, điểm `ai_match_score` trung bình, phân bố `<50%`, `50–75%`, `>75%` và số lượng theo `matching_version`.
   - Xử lý an toàn collection rỗng (`average_score = 0.0`), điểm `None`/`NaN`, và chuẩn hóa khoảng trắng dữ liệu legacy (`"CLOSED "` → `CLOSED`).
   - **Kết quả chạy trên `recruitment_db` thật:** `users: 13 (6 candidates, 5 recruiters, 2 admins)`, `companies: 5 (3 pending, 2 verified)`, `jobs: 9 (7 open, 2 closed, 0 hidden)`, `applications: 3 (3 applied)`, `ai_matching: total_scored=3, average_score=30.97 (<50%: 3), by_matching_version={'v1.0-SBERT': 3}` — khớp 100% tính toán thủ công `(31.3 + 30.7 + 30.9) / 3 = 30.97`.
2. **API Gateway WebSocket Proxy (`services/api-gateway/app/proxy/ws_proxy.py`):**
   - Route `@router.websocket("/ws/{path:path}")` chuyển tiếp `ws://localhost:8000/ws/chat/{conversation_id}?token={jwt}` xuống `ws://localhost:8001/ws/chat/{conversation_id}?token={jwt}`.
   - Forward đầy đủ path, query string, header `Authorization`, dữ liệu text/binary hai chiều và mã đóng kết nối (`4401`, `4404`, `1000`).
   - Đã khắc phục triệt để race condition handshake bằng cách mở xong kết nối upstream tới `:8001` trước khi gọi `websocket.accept()` với client, đồng thời giữ nguyên toàn bộ HTTP proxy (`core_proxy.py`, `ai_proxy.py`).
3. **Test chức năng & Integration Test:** `test_admin_statistics.py` (`2/2 PASSED`), `test_ws_proxy.py` (`4/4 PASSED`), và kiểm thử trực tiếp 2 client qua Gateway `:8000` + ngắt kết nối/kết nối lại (**PASSED**).

---

## 3. Tổng Hợp Kết Quả Thực Thi Kiểm Thử Mới Nhất

| Bộ kiểm thử | Lệnh thực thi | Kết quả |
|---|---|---|
| **Core Service Pytest** | `python -m pytest services/core-service/tests -o pythonpath=services/core-service -v` | **30 PASSED, 0 FAILED** (`8.05s`) |
| **API Gateway Pytest** | `python -m pytest services/api-gateway/tests -o pythonpath=services/api-gateway -v` | **4 PASSED, 0 FAILED** (`0.43s`) |
| **Read-Only Real DB Verification** | Kiểm tra đọc trực tiếp 13 users, 5 companies, 9 jobs, 3 applications thật trong `recruitment_db` | **PASS 100%** |
| **Live 5-Flow Integration Test** | Khởi chạy thật Gateway `:8000` + Core `:8001` + MongoDB `:27017` chạy trọn bộ Flows 1–5 + dọn sạch `[E2E]` | **5/5 Flows PASS 100%** |
| **Frontend Lint & Build** | `npm run lint` & `npm run build` trong `frontend/` | **0 errors, 0 warnings**; build thành công 132 modules (`386ms`) |
| **Browser Multi-Role & Multi-Viewport E2E** | Trình duyệt thật trên `http://127.0.0.1:5173` cho Recruiter, Candidate, Admin (`1366×768`, `1570×920`, `1920×1080`) | **PASS 100%** (`0` lỗi Console, `0` lỗi Network) |

---

## 4. Lưu Ý Vận Hành & Kết Luận Nghiệm Thu

1. **Về gửi Email SMTP ra Internet thực tế:** Cơ chế cấu hình qua biến môi trường `SMTP_*`, hàng đợi nền `FastAPI BackgroundTasks`, chống gửi trùng và xử lý lỗi đã hoàn thiện và được kiểm chứng thực tế qua TCP Loopback SMTP Server trong automated test (`test_task_9_3_smtp_loopback_and_failure_resilience`). Trong môi trường dev hiện tại, `SMTP_HOST` đang để trống để không dùng secret giả; khi triển khai thực tế chỉ cần điền `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` trong `services/core-service/.env`.
2. **Trạng thái Git & Cơ sở dữ liệu:**
   - Dữ liệu gốc trong `recruitment_db` được giữ nguyên vẹn 100% (`users: 13`, `companies: 5`, `job_postings: 9`, `applications: 3`, `skills_taxonomy: 147`, `conversations: 0`, `messages: 0`, `notifications: 0`).
   - Toàn bộ thay đổi đang nằm sạch trên working tree nhánh `main` (chưa thực hiện `git commit`, `git merge` hay `git push`).

### KẾT LUẬN CUỐI CÙNG: **PASS TOÀN BỘ TUẦN 10–11 (14/14 HẠNG MỤC ĐẠT YÊU CẦU)**
