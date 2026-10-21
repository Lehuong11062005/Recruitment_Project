# Frontend: Smart Recruitment Platform (ReactJS)

Giao diện cho hệ thống tuyển dụng. Công nghệ: **React 19, Vite, Tailwind CSS 4, Axios, React Router 7**.

## Chạy dự án

```bash
cd frontend
npm install
copy .env.example .env     # macOS/Linux: cp .env.example .env
npm run dev                # http://localhost:5173
```

Các lệnh khác: `npm run build` (đóng gói), `npm run lint` (kiểm tra code).

## Biến môi trường (`.env`, không commit)

| Biến | Ý nghĩa | Mặc định |
|---|---|---|
| `VITE_API_URL` | Địa chỉ API Gateway | `http://localhost:8000` |
| `VITE_MOCK_AUTH` | `true`: trang đăng nhập có 3 nút vào thẳng với vai trò CANDIDATE / RECRUITER / ADMIN (không cần backend). `false`: đăng nhập thật | `true` |

Sửa `.env` xong phải **tắt và chạy lại** `npm run dev`.

## Cấu trúc `src/` (theo `CauTruc.txt`)

```
src/
├── App.jsx              Routing phân quyền (Candidate, Recruiter, Admin)
├── main.jsx             BrowserRouter + AuthProvider
├── services/
│   ├── api.js           Axios trỏ về Gateway (http://localhost:8000), tự gắn JWT, xử lý 401
│   └── authService.js, jobService.js, applicationService.js, chatService.js
├── context/AuthContext.jsx   AuthProvider (token, user, login, logout)
├── hooks/useAuth.js
├── components/          PrivateRoute, GuestRoute, RootRedirect, PagePlaceholder, layouts/
├── pages/
│   ├── auth/            Login, Register
│   ├── candidate/       JobList (UC-C4), JobDetail (UC-C5), MyApplications + ApplicationDetail (UC-C7), Chat (UC-C8)
│   ├── recruiter/       ManageJobs
│   └── admin/           Dashboard
├── constants/           roles.js, status.js
└── utils/               storage, jwt, http
```

## Axios và API Gateway

- Mọi lời gọi API dùng `src/services/api.js`, ví dụ `const data = await jobService.searchJobs({ keyword: 'java' })`. Axios trả **thẳng body** (đã bỏ lớp `res.data`).
- Tự gắn header `Authorization: Bearer <access_token>`.
- Gặp lỗi **401** thì xóa phiên đăng nhập và đưa về `/login`.
- Gửi `FormData` (upload CV) thì tự bỏ `Content-Type` để trình duyệt đặt multipart.
- Lưu ý với người làm Gateway: frontend gọi `http://localhost:8000/api/v1/...` (khớp prefix `/api/v1` của core-service). Gateway cần chuyển tiếp đúng đường dẫn này sang Core Service.

## Đăng nhập và phân quyền

Response của `POST /api/v1/auth/login`: `{ access_token, token_type, user: { id, email, full_name, phone, role: "USER"|"ADMIN", user_type: "CANDIDATE"|"RECRUITER", company_id, status } }`.

Vai trò trong giao diện: `ADMIN` nếu `role = ADMIN`, ngược lại lấy `user_type` (cùng quy ước `get_role_claim` của core-service). Xem `src/constants/roles.js`.

`PrivateRoute` bọc nhóm route theo vai trò:

```jsx
<Route element={<PrivateRoute allowedRoles={[ROLES.CANDIDATE]} />}>
  <Route path="/candidate" element={<CandidateLayout />}>
    <Route path="jobs" element={<JobList />} />
  </Route>
</Route>
```

| Tình huống | Kết quả |
|---|---|
| Chưa đăng nhập vào trang riêng | `/login`, đăng nhập xong quay lại trang đang vào |
| Sai vai trò | `/403` |
| Đã đăng nhập vào `/login` | Về trang chủ theo vai trò |

Đây chỉ là chặn ở giao diện, backend vẫn phải kiểm tra quyền cho từng API.

## Route hiện có

| Đường dẫn | Trang | UC |
|---|---|---|
| `/login`, `/register` | Đăng nhập, đăng ký | UC-C1 |
| `/candidate` | Trang chủ ứng viên | |
| `/candidate/jobs` | Tìm kiếm việc làm | UC-C4 |
| `/candidate/jobs/:jobId` | Chi tiết JD + ứng tuyển | UC-C5 |
| `/candidate/applications`, `/candidate/applications/:applicationId` | Đơn ứng tuyển, chi tiết + lịch sử trạng thái | UC-C7 |
| `/candidate/messages`, `/candidate/messages/:conversationId` | Tin nhắn | UC-C8 |
| `/recruiter`, `/admin` | Trang chủ Recruiter, Admin | |
| `/recruiter/manage-jobs` | Tạo và theo dõi JD của nhà tuyển dụng | |
| `/recruiter/company-profile` | Cập nhật hồ sơ doanh nghiệp và trạng thái duyệt mềm | |
| `/403`, `*` | Không có quyền, không tìm thấy | |

## Lưu ý về API

`authService` dùng endpoint **thật** của core-service (`/api/v1/auth/...`). Các service `jobService`, `applicationService`, `chatService` là **giả định** vì router tương ứng của core-service còn trống; khi backend xong thì đối chiếu và sửa lại đường dẫn/tham số.

`recruiterService` dùng các endpoint công ty, kỹ năng và tin tuyển dụng của core-service. Router hiện chưa có endpoint liệt kê JD theo recruiter, nên bảng quản lý chỉ hiển thị các JD vừa tạo trong phiên hiện tại cho tới khi API danh sách được bổ sung.

## Quy ước làm việc nhóm

- Mỗi UC một file trong `src/pages/<vai trò>/`; gọi API qua `src/services/`, không gọi `axios` trực tiếp trong trang.
- Thêm route mới trong `src/App.jsx`; thêm mục menu trong file layout tương ứng ở `src/components/layouts/`.
- Không commit file `.env`.
