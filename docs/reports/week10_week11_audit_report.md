# BÁO CÁO AUDIT, IMPLEMENT & TEST TUẦN 10–11
## Smart Recruitment Platform (`Recruitment_Project`)

- **Ngày thực hiện:** 26/11/2026
- **Nhánh làm việc:** `main` (đã đồng bộ commit mới nhất `c680bca` từ `origin/main`)
- **Môi trường kiểm chứng:** Windows, Python 3.13.9, Node.js + Vite 8.3.0, MongoDB 8.2 (`localhost:27017`), Core Service (`:8001`), API Gateway (`:8000`), Frontend React 19 (`:5173`)

---

## 1. Executive Summary

| Chỉ số tổng hợp | Số lượng / Kết quả |
|---|---|
| **Tổng số hạng mục (task items) đã kiểm tra** | **12 hạng mục** (thuộc Tuần 10 & Tuần 11) |
| **Số hạng mục `PASS` ban đầu (trước khi sửa)** | **0 / 12** *(chưa đủ bằng chứng test tích hợp hoặc thiếu tính năng/lỗi race condition)* |
| **Số hạng mục `PARTIAL` ban đầu** | **10 / 12** |
| **Số hạng mục `FAIL` ban đầu** | **2 / 12** *(UC-C7 `ApplicationDetail.jsx` thiếu hoàn toàn UI theo dõi tiến trình/lịch phỏng vấn/lịch sử; `Chat.jsx` chỉ là trang tĩnh placeholder)* |
| **Số hạng mục `BLOCKED` ban đầu** | **0 / 12** |
| **Số hạng mục đã được hoàn thiện & xác minh** | **12 / 12** |
| **Kết quả cuối cùng toàn bộ Tuần 10–11** | **PASS TOÀN BỘ TUẦN 10–11** *(lưu ý minh bạch: SMTP thật ra Internet không cấu hình tài khoản thật trong `.env`, đã triển khai đầy đủ qua biến môi trường và kiểm chứng bằng Loopback SMTP Server trong automated test)* |

---

## 2. Initial Audit (Trước khi sửa code)

| Task | Hạng mục | File liên quan | Trạng thái ban đầu | Bằng chứng phát hiện khi Audit |
|---|---|---|---|---|
| **9.1** | HR Pipeline Backend (UC-R6) | `services/core-service/app/routers/applications.py`, `app/schemas/application.py`, `app/services/application_service.py` | **PARTIAL** | Đã có `PATCH /api/v1/applications/{id}/status`, kiểm tra `RECRUITER` và `job.recruiter_id`. Tuy nhiên: (1) gửi lại cùng `INTERVIEW` + cùng `interview_schedule` vẫn ghi trùng `status_history` và bắn trùng notification/email; (2) `get_application_detail` làm rơi `changed_by` và chỉ kiểm tra `company_id` thay vì `recruiter_id`; (3) chưa có pytest tự động cho endpoint này. |
| **9.1** | HR Pipeline Frontend & Khởi tạo Chat (UC-R6, UC-R7) | `frontend/src/pages/recruiter/CandidateRanking.jsx` | **PARTIAL** | Đã có dropdown đổi trạng thái, modal lịch phỏng vấn, `recruiter_note` và nút `"Nhắn tin cho ứng viên"`, nhưng **chưa hiển thị `status_history`** trên giao diện sau khi cập nhật và điều hướng tới `/recruiter/messages/...` thay vì `/recruiter/chat/...`. |
| **9.2** | Candidate Applications (UC-C7) | `services/core-service/app/services/application_service.py`, `frontend/src/pages/candidate/MyApplications.jsx`, `frontend/src/pages/candidate/ApplicationDetail.jsx` | **FAIL** | (1) Backend `GET /api/v1/applications/me` (`ApplicationResponse`) thiếu `status_history`, `interview_schedule`, thông tin chi tiết `job`/`company` và cờ xóa mềm `is_deleted`, chưa có tham số phân trang; (2) `ApplicationDetail.jsx` gọi nhầm `getAIAnalysis` thay vì `getApplicationDetail`, **thiếu hoàn toàn** thanh tiến trình 4 bước, thẻ lịch phỏng vấn và lịch sử trạng thái; (3) `MyApplications.jsx` chưa có thanh tiến trình phân biệt rõ `HIRED` vs `REJECTED`. |
| **9.3** | Notifications (Backend + UI) | `services/core-service/app/routers/notifications.py`, `app/services/notification_service.py`, `frontend/src/components/layouts/DashboardLayout.jsx` | **PARTIAL** | Backend đã có `GET /api/v1/notifications` và `PATCH /api/v1/notifications/{id}/read`, nhưng **Frontend hoàn toàn chưa có `notificationService.js` hay chuông thông báo** trên thanh Topbar để ứng viên nhìn thấy thông báo mới (Flow 1 & Flow 2). Ngoài ra `smoke_test_task_9_3_10_3.py` phụ thuộc `mongomock_motor` (chưa cài trong môi trường) và không được `pytest` thu thập. |
| **9.3** | Email Service | `services/core-service/app/services/email_service.py`, `app/core/config.py` | **PARTIAL** | Đã triển khai gửi qua `BackgroundTasks` và biến môi trường `SMTP_*`, không chặn API và không raise khi lỗi; tuy nhiên chưa có automated test kiểm chứng giao thức SMTP thực tế và chống gửi trùng khi không đổi lịch phỏng vấn. |
| **10.1** | Admin APIs (UC-A1, UC-A2, UC-A3) | `services/core-service/app/routers/admin.py`, `app/schemas/admin.py` | **PARTIAL** | Đã bảo vệ bằng `get_current_admin` (`role == "ADMIN"`), chặn tự khóa tài khoản (`409`). Tuy nhiên `PATCH /admin/jobs/{id}/status` chỉ cho phép `HIDDEN`/`DELETED` (chưa trả kèm `company_name` sau khi sửa), và `test_admin_moderation.py` mới chỉ test 401/403/409 chứ chưa kiểm thử thực tế với MongoDB. |
| **10.1** | Admin Statistics (UC-A4) | `services/core-service/app/services/admin_service.py`, `tests/test_admin_statistics.py` | **PARTIAL** | Logic tổng hợp đầy đủ 5 nhóm chỉ số và không gọi sai là AI Accuracy, nhưng test hiện có chỉ dùng mock `SimpleNamespace`, chưa kiểm chứng trên dữ liệu MongoDB thật và collection rỗng. |
| **10.2** | Admin Portal Frontend | `frontend/src/pages/admin/Dashboard.jsx`, `ManageUsers.jsx`, `ApproveCompanies.jsx`, `ModerateJobs.jsx`, `AdminLayout.jsx` | **PARTIAL** | Đã kết nối API thật, đúng bảng màu `#155EEF` / `#142B4A` / `#F5F8FC` / `#DCE5F0`, không dùng gradient; cần bổ sung thanh tab điều hướng nhanh giữa Dashboard và 3 phân hệ kiểm duyệt và kiểm chứng E2E trên trình duyệt. |
| **10.3** | Chat REST API | `services/core-service/app/models/chat.py`, `app/routers/chat.py`, `app/services/chat_service.py` | **PARTIAL** | Đã có 3 API `POST /api/v1/conversations`, `GET /api/v1/conversations`, `GET /api/v1/conversations/{id}/messages`. Tuy nhiên: (1) collection `conversations` thiếu unique compound index `(job_id, candidate_id)` chống race condition tạo phòng trùng; (2) khi `CANDIDATE` gửi `candidate_id` của người khác lên `POST /conversations`, hệ thống bỏ qua thay vì từ chối `403`. |
| **10.3** | Chat WebSocket (Core Service) | `services/core-service/app/routers/chat.py` | **PARTIAL** | **Phát hiện lỗi race condition nghiêm trọng:** `chat_websocket` gọi `await websocket.accept()` ở dòng đầu tiên **trước khi** truy vấn MongoDB (`_user_from_token`, `get_conversation_for_user`) và `manager.connect(room, websocket)`, khiến client nhận handshake `101` trước khi vào phòng chat, làm rớt tin nhắn đầu tiên khi 2 client kết nối sát nhau. |
| **10.3** | Chat Frontend | `frontend/src/pages/candidate/Chat.jsx`, `frontend/src/App.jsx` | **FAIL** | `Chat.jsx` hoàn toàn là giao diện placeholder tĩnh (`"CHƯA XÁC MINH API"`, ô nhập bị `disabled`), thiếu route `/candidate/chat` và `/recruiter/chat`, và thanh điều hướng Recruiter chưa có mục `Tin nhắn`. |
| **10.3** | API Gateway WebSocket Proxy | `services/api-gateway/app/proxy/ws_proxy.py` | **PARTIAL** | **Phát hiện lỗi race condition handshake tương tự:** Gateway gọi `await websocket.accept()` với trình duyệt **trước khi** mở kết nối upstream `websockets.connect` tới Core Service `:8001` (trên Windows tốn ~300ms phân giải `localhost`), khiến tin nhắn gửi ngay sau `onopen` hoặc giữa 2 client qua `:8000` bị lỡ nhịp; đồng thời chưa truyền mã đóng khi upstream kết thúc bình thường. |

---

## 3. Implementation Log (Nhật ký sửa lỗi & hoàn thiện)

### 3.1. Backend Core Service
1. **Hoàn thiện dữ liệu UC-C7 & Chống trùng lặp thông báo/lịch sử UC-R6 (`app/schemas/application.py`, `app/routers/applications.py`, `app/services/application_service.py`)**:
   - **Vấn đề & nguyên nhân:** `ApplicationResponse` thiếu `status_history`, `interview_schedule`, thông tin chi tiết `job`/`company` (kèm trạng thái xóa mềm `is_deleted`); `update_application_status` tạo bản ghi lịch sử và thông báo trùng khi HR lưu ghi chú nhưng giữ nguyên `INTERVIEW` và `interview_schedule`.
   - **Giải pháp:**
     - Bổ sung `ApplicationJobBrief`, `ApplicationCompanyBrief`, `status_history`, `interview_schedule` vào `ApplicationResponse` (giữ nguyên `job_title`, `company_name` để tương thích ngược 100% và tuyệt đối không lộ `recruiter_note` cho Candidate).
     - Bổ sung phân trang `skip`/`limit` và gom truy vấn (`$in`) cho `GET /api/v1/applications/me`.
     - Kiểm tra `schedule_changed = schedule is not None and schedule != app.interview_schedule` trong `update_application_status`; chuẩn hóa kiểm tra quyền sở hữu `job.recruiter_id == user.id` cho cả xem chi tiết lẫn cập nhật trạng thái.
2. **Đảm bảo thứ tự thông báo & Admin Moderation (`app/routers/notifications.py`, `app/routers/admin.py`, `app/schemas/admin.py`, `app/main.py`)**:
   - Sắp xếp thông báo theo `[("created_at", -1), ("_id", -1)]` để ổn định thứ tự khi hai thông báo phát sinh cùng mili-giây.
   - Cho phép `AdminJobStatusUpdate` hỗ trợ `OPEN | CLOSED | HIDDEN | DELETED` (xóa mềm gán `status="HIDDEN"` và `deleted_at`) đồng thời trả kèm `company_name`.
   - Dọn dòng import trùng lặp trong `app/main.py`.
3. **Unique Index & Khắc phục Race Condition WebSocket Chat (`app/models/chat.py`, `app/services/chat_service.py`, `app/routers/chat.py`)**:
   - Thêm `IndexModel([("job_id", ASCENDING), ("candidate_id", ASCENDING)], unique=True, name="unique_job_candidate_conversation")` và bắt `DuplicateKeyError` trong `get_or_create_conversation`.
   - Chặn `403` nếu `CANDIDATE` truyền `candidate_id` của người khác vào `POST /api/v1/conversations`.
   - Trong `chat_websocket`: thực hiện xác thực JWT (`_user_from_token`) và kiểm tra quyền phòng (`get_conversation_for_user`) **trước**, sau đó mới gọi `await websocket.accept()` và `manager.connect(room, websocket)` trong cùng một nhịp đồng bộ (các nhánh lỗi vẫn `accept()` rồi `close(4401/4404)` để client nhận đúng mã lỗi).

### 3.2. Backend API Gateway
4. **Khắc phục Race Condition WebSocket Proxy & Xử lý lỗi Upstream (`services/api-gateway/app/proxy/ws_proxy.py`, `core_proxy.py`, `ai_proxy.py`)**:
   - Mở kết nối upstream `async with upstream_cm as upstream:` tới Core Service `:8001` hoàn tất rồi mới gọi `await websocket.accept()` phía trình duyệt, bảo đảm khi sự kiện `onopen` kích hoạt ở Frontend thì toàn bộ đường truyền `Browser <-> Gateway (:8000) <-> Core (:8001)` đã thông suốt.
   - Truyền chính xác mã đóng kết nối (`4401`, `4404`, `1000`) từ Core Service về Client.
   - Bọc `httpx.RequestError` trong `core_proxy.py` và `ai_proxy.py` trả về `502 Bad Gateway` rõ ràng thay vì lỗi 500 không kiểm soát khi service đích tắt.

### 3.3. Frontend React
5. **Chuông thông báo Topbar (`src/services/notificationService.js`, `src/components/NotificationBell.jsx`, `src/components/layouts/DashboardLayout.jsx`)**:
   - Tích hợp `GET /api/v1/notifications` và `PATCH /api/v1/notifications/{id}/read`, hiển thị số lượng chưa đọc, danh sách thông báo mới nhất và điều hướng thẳng tới đơn ứng tuyển khi bấm vào.
6. **Theo dõi đơn ứng tuyển UC-C7 (`src/components/PipelineProgress.jsx`, `src/pages/candidate/MyApplications.jsx`, `src/pages/candidate/ApplicationDetail.jsx`)**:
   - Xây dựng thanh tiến trình 4 bước (`Đã nộp` → `Đang sơ loại` → `Hẹn phỏng vấn` → `Kết quả`), phân biệt rõ màu xanh lá thành công khi `HIRED` (`Kết quả: Trúng tuyển`) và màu đỏ từ chối khi `REJECTED` (`Kết quả: Từ chối`).
   - Cập nhật `ApplicationDetail.jsx` gọi `GET /api/v1/applications/{id}`, hiển thị đầy đủ thông tin công việc/công ty (kể cả khi tin bị xóa mềm), thẻ `Lịch phỏng vấn`, timeline `Lịch sử thay đổi trạng thái`, xem trước CV PDF và phân tích AI.
7. **HR Pipeline & Khởi tạo Chat UC-R6/UC-R7 (`src/pages/recruiter/CandidateRanking.jsx`)**:
   - Bổ sung danh sách `Lịch sử thay đổi trạng thái` cập nhật tức thời sau mỗi thao tác lưu trạng thái/lịch phỏng vấn; cập nhật nút `"Nhắn tin cho ứng viên"` điều hướng tới `/recruiter/chat/{conversationId}`.
8. **Chat Realtime 2 cột 30%/70% (`src/pages/common/ChatPage.jsx`, `src/pages/candidate/Chat.jsx`, `src/App.jsx`, `src/config/env.js`)**:
   - Triển khai `ChatPage.jsx` dùng chung cho `/candidate/chat` và `/recruiter/chat` (đồng thời tương thích ngược với `/candidate/messages` và `/recruiter/messages`).
   - Bố cục 2 cột chuẩn 30% (danh sách hội thoại, tìm kiếm, `last_message`, `updated_at`, số tin chưa đọc) và 70% (lịch sử tin nhắn, trạng thái kết nối WebSocket, khung nhập và nút gửi).
   - Kết nối WebSocket qua API Gateway (`ws://localhost:8000/ws/chat/{id}?token=...`), chống mở kết nối trùng, đóng sạch khi chuyển hội thoại/unmount, tự động reconnect theo cấp số nhân khi đứt mạng (trừ mã lỗi xác thực `4401`/`4403`/`4404`), khử trùng lặp theo `message.id` và cô lập tin nhắn theo đúng `conversation_id`.
9. **Admin Portal (`src/components/layouts/AdminLayout.jsx`, `src/index.css`)**:
   - Bổ sung thanh tab điều hướng đồng bộ giữa Tổng quan thống kê, Quản lý người dùng, Duyệt doanh nghiệp và Kiểm duyệt tin tuyển dụng theo đúng quy chuẩn thiết kế (`#155EEF`, `#142B4A`, `#F5F8FC`, `#DCE5F0`, `#64748B`, font Inter, bo góc 8px/12px, không gradient).

---

## 4. Test Evidence (Bằng chứng kiểm thử)

### 4.1. Automated Tests — Core Service (Unit + Real MongoDB Isolated Integration + Loopback SMTP + Uvicorn WebSocket)
- **Lệnh thực thi:**
  ```powershell
  python -m pytest services/core-service/tests -o pythonpath=services/core-service -v
  ```
- **Kết quả thực tế:** **30 PASSED, 0 FAILED** (thời gian chạy: `8.44s`), sử dụng database cô lập `recruitment_test_week10_11` trên MongoDB thật.
- **Chi tiết các nhóm test trong `test_week10_11_integration.py`:**
  - `test_task_9_1_and_9_3_pipeline_permissions_history_interview_and_notifications`: **PASSED** (kiểm tra quyền HR sở hữu / HR khác cùng công ty / HR công ty khác / Candidate, validate trạng thái sai 422, lưu lịch phỏng vấn, chống ghi trùng lịch sử & email khi không có thay đổi, API đọc/đánh dấu thông báo, khả năng chịu lỗi khi tầng notification gặp sự cố).
  - `test_task_9_3_smtp_loopback_and_failure_resilience`: **PASSED** (dựng TCP SMTP Server loopback cục bộ xác nhận nhận đủ bản tin MIME HTML/Text, và xác nhận trả `False` an toàn khi cổng SMTP sập).
  - `test_task_9_2_candidate_applications_isolation_and_soft_deleted_job`: **PASSED** (kiểm tra ứng viên có đơn, ứng viên chưa có đơn, chặn xem đơn người khác `404`, ẩn `recruiter_note`, xử lý job bị Admin xóa mềm `is_deleted=True`).
  - `test_task_10_1_admin_moderation_and_statistics_with_real_mongodb`: **PASSED** (kiểm tra RBAC `401`/`403`, thống kê trên DB rỗng & DB có dữ liệu kèm điểm `None`/`<50`/`50-75`/`>75`, tìm kiếm user, khóa/mở khóa, chặn tự khóa `409`, duyệt/từ chối công ty, ẩn tin và bảo toàn đơn ứng tuyển).
  - `test_task_10_3_chat_rest_and_realtime_websocket`: **PASSED** (chạy Uvicorn thật + 2 kết nối `websockets` đồng thời của HR & Candidate, xác minh từ chối JWT sai `4401` / người lạ `4404`, trao đổi realtime 2 chiều, cập nhật `last_message`/`updated_at` và bảo toàn lịch sử sau ngắt kết nối).
  - Toàn bộ 25 test của Tuần 1–9 (`test_week9_apis.py`, `test_profile_export.py`, `test_skill_mapping.py`, `test_admin_moderation.py`, `test_admin_statistics.py`): **25/25 PASSED** (không gây hồi quy).

### 4.2. Automated Tests — API Gateway (HTTP & WebSocket Proxy)
- **Lệnh thực thi:**
  ```powershell
  python -m pytest services/api-gateway/tests -o pythonpath=services/api-gateway -v
  ```
- **Kết quả thực tế:** **4 PASSED, 0 FAILED** (`0.51s`) — xác minh chuyển đổi `http/https -> ws/wss`, giữ nguyên query `?token=...`, chuyển tiếp header `Authorization`, truyền mã đóng `4401` từ upstream và giữ nguyên HTTP health endpoint.

### 4.3. Frontend Lint & Production Build
- **Lệnh thực thi:**
  ```powershell
  cd frontend
  npm run lint
  npm run build
  ```
- **Kết quả thực tế:**
  - `eslint .`: **0 errors, 0 warnings**.
  - `vite build`: **PASS** (`✓ 132 modules transformed`, xuất `dist/index.html`, `dist/assets/index-*.css`, `dist/assets/index-*.js` trong `406ms`).

### 4.4. Live End-to-End Verification (Network + Real Browser UI)
1. **Kiểm thử mạng trực tiếp (`Gateway :8000 -> Core :8001 -> MongoDB :27017`):**
   - Toàn bộ **FLOW 1 → FLOW 5** đều **PASS 100%**:
     - Kết nối WebSocket trực tiếp `:8001` (`ping -> pong`) và kết nối 2 client độc lập qua Gateway `:8000` (`ws://127.0.0.1:8000/ws/chat/{id}?token=...`), trao đổi tin nhắn 2 chiều, ngắt kết nối và kết nối lại thành công.
     - Đối chiếu số liệu `GET /api/v1/admin/statistics` khớp 100% với kết quả đếm thủ công trực tiếp trên các collection MongoDB.
2. **Kiểm thử giao diện thực tế trên trình duyệt (`http://127.0.0.1:5173`):**
   - **Recruiter (`e2e.hr@example.com`):** Đăng nhập → Mở bảng xếp hạng ứng viên → Xem điểm AI (`90%`), trạng thái `INTERVIEW`, lịch phỏng vấn và `Lịch sử thay đổi trạng thái` → Cập nhật `recruiter_note` thành công → Bấm `"Nhắn tin cho ứng viên"` điều hướng sang `/recruiter/chat/{id}`, hiển thị `Đã kết nối realtime`, gửi tin nhắn thành công và cập nhật ngay `last_message` ở cột trái.
   - **Candidate (`e2e.cand@example.com`):** Đăng nhập → Mở chuông thông báo (`2 chưa đọc`), bấm thông báo chuyển tới `ApplicationDetail` (số chưa đọc giảm còn `1`) → Xác nhận thanh tiến trình 4 bước, thẻ `Lịch phỏng vấn`, `Lịch sử thay đổi trạng thái`, và xác nhận `recruiter_note` hoàn toàn không xuất hiện trong DOM/HTML → Vào `/candidate/chat` thấy tin nhắn của HR, gửi phản hồi realtime, reload trang và xác nhận cả 2 tin nhắn được giữ nguyên.
   - **Admin (`e2e.admin@example.com`):** Đăng nhập `/admin` → Xác nhận 4 thẻ thống kê và 3 biểu đồ khớp backend → Tìm kiếm user ở `/admin/users` (tài khoản đang đăng nhập hiển thị `Tài khoản của bạn`, không có nút tự khóa) → Duyệt công ty `PENDING -> VERIFIED` ở `/admin/companies` → Ẩn tin tuyển dụng ở `/admin/jobs` → Quay lại Dashboard xác nhận số liệu cập nhật tức thời.
   - Sau khi kiểm thử xong, toàn bộ bản ghi tạm `[E2E]` đã được dọn sạch, dữ liệu gốc trong `recruitment_db` được bảo toàn nguyên vẹn (`13 users`, `5 companies`, `9 job_postings`, `3 applications`).

---

## 5. API Verification

| Method | Endpoint (qua Gateway `:8000`) | Auth / Role | Request Body / Query chính | Expected Response | Actual Result | Kết quả |
|---|---|---|---|---|---|---|
| `PATCH` | `/api/v1/applications/{id}/status` | JWT (`RECRUITER` sở hữu job) | `{ pipeline_status, recruiter_note?, interview_schedule? }` | `200 OK` + `ApplicationStatusResponse`; `403` nếu sai HR/role; `422` nếu thiếu lịch khi `INTERVIEW` | Trả đúng `200` / `403` / `422`, ghi `status_history`, tạo notification + background email | **PASS** |
| `GET` | `/api/v1/applications/me` | JWT (`CANDIDATE`) | `?skip=0&limit=50` | `200 OK` mảng `ApplicationResponse` (kèm `job`, `company`, `status_history`, `interview_schedule`) | Trả đúng đơn của chính ứng viên, không lộ `recruiter_note`, xử lý job xóa mềm | **PASS** |
| `GET` | `/api/v1/applications/{id}` | JWT (`CANDIDATE` chủ đơn hoặc `RECRUITER` chủ job) | — | `200 OK` `ApplicationDetailResponse`; `404` nếu không có quyền | Ứng viên thấy tiến trình & lịch phỏng vấn (`recruiter_note=null`); HR thấy đầy đủ | **PASS** |
| `GET` | `/api/v1/notifications` | JWT (mọi user) | `?unread_only=false&limit=50&skip=0` | `200 OK` danh sách thông báo của user hiện tại (mới nhất trước) | Trả đúng danh sách theo thứ tự thời gian giảm dần, cô lập hoàn toàn giữa các user | **PASS** |
| `PATCH` | `/api/v1/notifications/{id}/read` | JWT (chủ sở hữu thông báo) | — | `200 OK` (`is_read: true`); `404` nếu của user khác | Cập nhật `is_read: true` cho chủ sở hữu, trả `404` với user khác | **PASS** |
| `GET` | `/api/v1/admin/users` | JWT (`ADMIN`) | `?q=&role=&user_type=&status=&page=1&limit=20` | `200 OK` `AdminPage[AdminUserItem]`; `403` nếu không phải `ADMIN` | Lọc & tìm kiếm chính xác theo tên/email, từ chối `401`/`403` đúng | **PASS** |
| `PATCH` | `/api/v1/admin/users/{id}/status` | JWT (`ADMIN`) | `{ "status": "ACTIVE" \| "BANNED" }` | `200 OK`; `409` nếu Admin tự khóa chính mình | Khóa/mở khóa thành công, chặn tự khóa `409`, user bị khóa bị chặn `403` ngay | **PASS** |
| `GET` | `/api/v1/admin/companies` | JWT (`ADMIN`) | `?verification_status=PENDING\|VERIFIED\|REJECTED` | `200 OK` `AdminPage[AdminCompanyItem]` | Lọc đúng trạng thái kiểm duyệt doanh nghiệp | **PASS** |
| `PATCH` | `/api/v1/admin/companies/{id}/verify` | JWT (`ADMIN`) | `{ "verification_status": "VERIFIED" \| "REJECTED" }` | `200 OK` `AdminCompanyItem` | Lưu đúng `verification_status` vào MongoDB | **PASS** |
| `GET` | `/api/v1/admin/jobs` | JWT (`ADMIN`) | `?status=OPEN\|CLOSED\|HIDDEN` | `200 OK` `AdminPage[AdminJobItem]` (kèm `company_name`) | Trả danh sách tin chưa xóa mềm kèm tên công ty | **PASS** |
| `PATCH` | `/api/v1/admin/jobs/{id}/status` | JWT (`ADMIN`) | `{ "status": "HIDDEN" \| "DELETED" }` | `200 OK` `AdminJobItem` | Ẩn tin hoặc gán `deleted_at` (xóa mềm), ẩn khỏi tìm kiếm nhưng giữ nguyên `applications` | **PASS** |
| `GET` | `/api/v1/admin/statistics` | JWT (`ADMIN`) | — | `200 OK` `AdminStatisticsResponse` | Khớp 100% truy vấn thủ công MongoDB cho users, companies, jobs, applications, AI matching | **PASS** |
| `POST` | `/api/v1/conversations` | JWT (`RECRUITER` / `CANDIDATE`) | `{ job_id, candidate_id? }` | `200 OK` `ConversationResponse` (idempotent) | Tạo mới hoặc trả hội thoại cũ, chặn `403` nếu HR không sở hữu job hoặc ứng viên chưa nộp đơn | **PASS** |
| `GET` | `/api/v1/conversations` | JWT (`RECRUITER` / `CANDIDATE`) | — | `200 OK` danh sách hội thoại mới nhất lên đầu | Có `other_user`, `job_title`, `last_message`, `unread_count`, `updated_at` | **PASS** |
| `GET` | `/api/v1/conversations/{id}/messages` | JWT (thành viên hội thoại) | `?limit=50&before=` | `200 OK` lịch sử cũ → mới; `404` nếu người ngoài | Trả đúng lịch sử, tự đánh dấu đã đọc, chặn người ngoài `404` | **PASS** |
| `WS` | `ws://localhost:8000/ws/chat/{id}?token={jwt}` | JWT query param | `{"event":"message","content":"..."}` | Proxy 2 chiều xuống `ws://localhost:8001/ws/chat/{id}` | Đồng bộ realtime giữa 2 client, lưu `messages`, cập nhật `conversations`, đóng `4401`/`4404` khi không hợp lệ | **PASS** |

---

## 6. Database Verification

Đã kiểm tra trực tiếp trên MongoDB (`recruitment_db` tại `localhost:27017`) sau khi Beanie đồng bộ index:

| Collection | Cấu trúc trường xác minh | Indexes thực tế trên MongoDB | Tính nhất quán & Quan hệ dữ liệu |
|---|---|---|---|
| `users` | `email`, `password_hash`, `full_name`, `role`, `user_type`, `company_id`, `profile`, `status`, `deleted_at` | `_id_`, `email_1` (unique), `company_id_1` | Phân tách rõ `role` (`ADMIN`/`USER`) và `user_type` (`CANDIDATE`/`RECRUITER`). |
| `companies` | `name`, `industry`, `address`, `website`, `description`, `verification_status`, `deleted_at` | `_id_`, `name_1` (unique) | Chỉ công ty `VERIFIED` mới hiển thị tin tuyển dụng công khai cho ứng viên. |
| `job_postings` | `company_id`, `recruiter_id`, `title`, `description`, `required_skills`, `status`, `deleted_at` | `_id_`, `title_text_description_text`, `company_id_1_deleted_at_1`, `recruiter_id_1` | Xóa mềm qua `deleted_at` không làm mất khóa ngoại từ `applications` hay `conversations`. |
| `applications` | `job_id`, `candidate_id`, `cv_url`, `pipeline_status`, `status_history`, `interview_schedule`, `recruiter_note`, `ai_match_score`, `matching_version` | `_id_`, `unique_job_candidate_application` (unique `job_id + candidate_id`), `candidate_id_1`, `job_id_1_ai_match_score_-1` | Không thể nộp đơn trùng; `status_history` chỉ nối thêm (append-only), không ghi đè lịch sử cũ. |
| `notifications` | `user_id`, `title`, `content`, `type` (`APPLICATION_STATUS`), `action_url`, `is_read`, `created_at`, `expire_at` | `_id_`, `user_id_1_is_read_1`, `expire_at_1` | Gắn đúng `candidate_id` nhận thông báo; không phát sinh bản ghi trùng khi không đổi trạng thái/lịch. |
| `conversations` | `job_id`, `candidate_id`, `recruiter_id`, `last_message`, `updated_at` | `_id_`, `unique_job_candidate_conversation` (unique `job_id + candidate_id`), `candidate_id_1`, `recruiter_id_1` | Chống tạo trùng phòng chat ở cả tầng nghiệp vụ lẫn tầng unique index của MongoDB. |
| `messages` | `conversation_id`, `sender_id`, `sender_role`, `message_type`, `content`, `attachments`, `is_read`, `created_at` | `_id_`, `conversation_id_1_created_at_-1` | Mọi tin nhắn qua WebSocket đều được lưu bền vững vào `messages` và cập nhật `conversations.last_message` + `updated_at`. |

*Không có bất kỳ collection mới hay dữ liệu trùng lặp nào bị tạo thêm ngoài thiết kế chuẩn.*

---

## 7. Final Task Checklist

| Task | Hạng mục | Người phụ trách gốc | Trạng thái cuối cùng | Ghi chú xác minh |
|---|---|---|---|---|
| **9.1** | HR Pipeline Backend (UC-R6) | Mạnh | **PASS** | Phân quyền chặt, lưu lịch phỏng vấn & lịch sử chuẩn, chống thông báo trùng, pass pytest & E2E. |
| **9.1** | HR Pipeline Frontend & Khởi tạo Chat (UC-R6, UC-R7) | Mạnh | **PASS** | Đổi trạng thái, modal lịch phỏng vấn, ghi chú nội bộ, lịch sử trạng thái và mở chat hoạt động thật trên trình duyệt. |
| **9.2** | Candidate Applications Backend & Frontend (UC-C7) | Hùng | **PASS** | `MyApplications.jsx` & `ApplicationDetail.jsx` hiển thị thanh tiến trình 4 bước (phân biệt rõ `HIRED` vs `REJECTED`), lịch phỏng vấn, lịch sử trạng thái và xử lý job xóa mềm. |
| **9.3** | Notification Backend & Frontend Bell | Cường (+ bổ sung UI) | **PASS** | API thông báo + chuông thông báo trên Topbar đồng bộ realtime/polling, đánh dấu đã đọc và điều hướng chính xác. |
| **9.3** | Email Service (BackgroundTasks + SMTP) | Cường | **PASS** | Cấu hình qua biến môi trường `SMTP_*`, chạy nền qua `BackgroundTasks`, đã kiểm chứng giao thức SMTP qua Loopback Server & khả năng chịu lỗi. |
| **10.1** | Admin Moderation APIs (UC-A1, UC-A2, UC-A3) | Nam | **PASS** | Bảo vệ `ADMIN` ở backend, lọc/tìm kiếm, khóa/mở khóa, duyệt/từ chối công ty, ẩn/xóa mềm tin tuyển dụng an toàn. |
| **10.1** | Admin Statistics API (UC-A4) | Hưởng | **PASS** | Đối chiếu khớp 100% với truy vấn MongoDB trực tiếp, xử lý điểm `null` và collection rỗng chính xác. |
| **10.2** | Admin Portal Frontend | Nam | **PASS** | Dashboard thẻ số liệu, biểu đồ và 3 phân hệ quản trị hoạt động với API thật, đúng chuẩn UI. |
| **10.3** | Chat REST API | Cường | **PASS** | Tạo/lấy phòng chat idempotent (có unique index), danh sách hội thoại và lịch sử tin nhắn phân quyền chặt chẽ. |
| **10.3** | Chat WebSocket (Core Service) | Cường | **PASS** | Đã sửa race condition `accept()`, xác thực JWT, broadcast 2 client đồng thời và lưu MongoDB bền vững. |
| **10.3** | Chat Frontend (`ChatPage.jsx`) | Hùng | **PASS** | Giao diện 2 cột 30%/70% dùng chung cho Candidate & Recruiter, đồng bộ REST + WebSocket qua Gateway, tự reconnect và không lẫn hội thoại. |
| **10.3** | API Gateway WebSocket Proxy | Hưởng | **PASS** | Đã sửa race condition handshake upstream, proxy 2 chiều `ws://localhost:8000/ws/chat/{id}` xuống `:8001` ổn định, giữ nguyên các HTTP proxy hiện có. |

---

## 8. Remaining Issues & Operational Notes

1. **Cấu hình tài khoản SMTP thực tế ngoài Internet (Môi trường triển khai):**
   - Trong file `services/core-service/.env` của máy phát triển hiện chưa điền thông tin tài khoản Gmail/SMTP thật (`SMTP_HOST` để trống theo đúng cơ chế an toàn trong `.env.example`, không hardcode secret giả).
   - Khi chạy ở môi trường dev chưa điền `SMTP_HOST`, hệ thống tự động ghi log bỏ qua gửi mail ngoài Internet mà không ảnh hưởng tới thông báo trong ứng dụng. Toàn bộ luồng đóng gói MIME HTML/Text, đăng nhập/gửi qua `smtplib.SMTP` và chạy nền qua `FastAPI BackgroundTasks` đã được xác minh thực tế bằng Loopback SMTP Server trong automated test (`test_task_9_3_smtp_loopback_and_failure_resilience`). Khi triển khai thực tế chỉ cần khai báo `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` trong `services/core-service/.env`.
2. **Kiến trúc `ConnectionManager` của WebSocket Chat:**
   - `ConnectionManager` hiện quản lý danh sách kết nối theo phòng trong bộ nhớ tiến trình (in-memory), hoàn toàn phù hợp khi chạy Core Service với 1 worker Uvicorn chuẩn của đồ án. Nếu sau này mở rộng nhiều worker song song, cần bổ sung Redis Pub/Sub.
3. **Cảnh báo deprecation của thư viện bên thứ ba:**
   - Khi chạy `pytest` trên Python 3.13 có xuất hiện các `DeprecationWarning` từ nội bộ `beanie`/`lazy-model`/`python-jose` (`datetime.utcnow()`, `model_fields`); đây là cảnh báo từ thư viện phụ thuộc, không gây lỗi runtime.
