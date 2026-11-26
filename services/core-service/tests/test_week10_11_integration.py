"""Integration Test Suite cho toàn bộ chức năng Backend Tuần 10–11 (Smart Recruitment Platform).

Sử dụng MongoDB thật tại localhost:27017 với database cô lập riêng (`recruitment_test_week10_11`)
để kiểm증 đầy đủ Beanie ODM, MongoDB indexes, FastAPI routers, JWT Auth/RBAC, BackgroundTasks,
SMTP loopback và WebSocket 2 chiều mà KHÔNG chạm tới dữ liệu thật trong `recruitment_db`.
"""
import os
import socketserver
import threading
from datetime import datetime, timedelta, timezone
from typing import List

import pytest
from beanie import init_beanie
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.websockets import WebSocketDisconnect

from app.core import database as db_module
from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.application import AIAnalysis, Application, StatusHistory
from app.models.chat import Conversation, Message
from app.models.company import Company
from app.models.job import JobPosting
from app.models.notification import Notification
from app.models.skill import SkillsTaxonomy
from app.models.user import CandidateProfile, User
from app.services import email_service, notification_service

TEST_DB_URI = "mongodb://localhost:27017/recruitment_test_week10_11"
ALL_MODELS = [
    User,
    Company,
    SkillsTaxonomy,
    JobPosting,
    Application,
    Notification,
    Conversation,
    Message,
]


async def _drop_isolated_db():
    client = AsyncIOMotorClient(TEST_DB_URI)
    db_name = client.get_default_database().name
    assert db_name == "recruitment_test_week10_11"
    await client.drop_database(db_name)
    client.close()


@pytest.fixture
def isolated_client(monkeypatch):
    """Khởi tạo TestClient gắn với database MongoDB cô lập `recruitment_test_week10_11`."""
    import asyncio

    monkeypatch.setattr(db_module, "MONGO_URI", TEST_DB_URI)
    # Tắt SMTP thật mặc định để các test API chạy độc lập, trừ test SMTP chuyên biệt
    monkeypatch.setattr(settings, "SMTP_HOST", "")

    asyncio.run(_drop_isolated_db())
    with TestClient(app) as client:
        yield client
    asyncio.run(_drop_isolated_db())


def _auth_header(user: User) -> dict:
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"Authorization": f"Bearer {token}"}


def _raw_token(user: User) -> str:
    return create_access_token({"sub": str(user.id), "role": user.role})


def _seed_base_entities(client: TestClient):
    async def _create():
        comp_a = Company(
            name="Alpha Tech Corp",
            industry="Software",
            address="TP.HCM",
            verification_status="VERIFIED",
        )
        comp_b = Company(
            name="Beta Data Ltd",
            industry="AI",
            address="Hà Nội",
            verification_status="PENDING",
        )
        await comp_a.insert()
        await comp_b.insert()

        admin = User(
            email="admin@example.com",
            password_hash=hash_password("Admin123!"),
            full_name="System Admin",
            role="ADMIN",
            user_type=None,
        )
        hr_owner = User(
            email="hr.owner@example.com",
            password_hash=hash_password("Hr123456!"),
            full_name="HR Mạnh",
            role="USER",
            user_type="RECRUITER",
            company_id=comp_a.id,
        )
        hr_same_co = User(
            email="hr.colleague@example.com",
            password_hash=hash_password("Hr123456!"),
            full_name="HR Đồng Nghiệp",
            role="USER",
            user_type="RECRUITER",
            company_id=comp_a.id,
        )
        hr_other_co = User(
            email="hr.other@example.com",
            password_hash=hash_password("Hr123456!"),
            full_name="HR Công Ty Khác",
            role="USER",
            user_type="RECRUITER",
            company_id=comp_b.id,
        )
        cand_1 = User(
            email="cand1@example.com",
            password_hash=hash_password("Cand1234!"),
            full_name="Ứng viên Hùng",
            role="USER",
            user_type="CANDIDATE",
            profile=CandidateProfile(summary="Python & React developer", location="TP.HCM"),
        )
        cand_2 = User(
            email="cand2@example.com",
            password_hash=hash_password("Cand1234!"),
            full_name="Ứng viên Nam",
            role="USER",
            user_type="CANDIDATE",
        )
        for u in (admin, hr_owner, hr_same_co, hr_other_co, cand_1, cand_2):
            await u.insert()

        skill_py = SkillsTaxonomy(name="Python", category="Backend", aliases=["py"])
        await skill_py.insert()

        job_1 = JobPosting(
            company_id=comp_a.id,
            recruiter_id=hr_owner.id,
            title="Senior FastAPI Engineer",
            description="Xây dựng microservices với FastAPI & MongoDB",
            required_skills=[skill_py.id],
            level="SENIOR",
            location="TP.HCM",
            status="OPEN",
        )
        job_2 = JobPosting(
            company_id=comp_b.id,
            recruiter_id=hr_other_co.id,
            title="Data Scientist",
            description="Machine Learning",
            level="MID",
            location="Hà Nội",
            status="CLOSED",
        )
        await job_1.insert()
        await job_2.insert()

        app_1 = Application(
            job_id=job_1.id,
            candidate_id=cand_1.id,
            cv_url=f"/uploads/cvs/{cand_1.id}/sample.pdf",
            parsed_text="Kinh nghiệm FastAPI, Python, MongoDB",
            pipeline_status="APPLIED",
            status_history=[StatusHistory(status="APPLIED", changed_by=cand_1.id)],
            ai_match_score=84.5,
            matching_version="v1.0",
            ai_status="DONE",
            ai_analysis=AIAnalysis(
                matched=[skill_py.id],
                missing=[],
                score_breakdown={"skill_score": 100.0, "semantic_score": 78.0},
                recommendation="Ứng viên phù hợp tốt.",
            ),
        )
        await app_1.insert()

        return {
            "comp_a": comp_a,
            "comp_b": comp_b,
            "admin": admin,
            "hr_owner": hr_owner,
            "hr_same_co": hr_same_co,
            "hr_other_co": hr_other_co,
            "cand_1": cand_1,
            "cand_2": cand_2,
            "job_1": job_1,
            "job_2": job_2,
            "app_1": app_1,
        }

    return client.portal.call(_create)


# ==============================================================================
# TASK 9.1 (UC-R6) & TASK 9.3: PIPELINE TUYỂN DỤNG + NOTIFICATION + EMAIL
# ==============================================================================
def test_task_9_1_and_9_3_pipeline_permissions_history_interview_and_notifications(
    isolated_client: TestClient, monkeypatch
):
    ctx = _seed_base_entities(isolated_client)
    app_id = str(ctx["app_1"].id)
    sent_emails: List[tuple] = []
    monkeypatch.setattr(
        email_service,
        "send_email",
        lambda to_email, subject, body_text, body_html=None: sent_emails.append(
            (to_email, subject, body_text)
        )
        or True,
    )

    # 1. Candidate không được phép đổi trạng thái -> 403
    r_cand = isolated_client.patch(
        f"/api/v1/applications/{app_id}/status",
        json={"pipeline_status": "SCREENING"},
        headers=_auth_header(ctx["cand_1"]),
    )
    assert r_cand.status_code == 403

    # 2. Recruiter công ty khác & Recruiter khác cùng công ty không sở hữu job -> 403
    for unauthorized_hr in (ctx["hr_other_co"], ctx["hr_same_co"]):
        r_unauth = isolated_client.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"pipeline_status": "SCREENING"},
            headers=_auth_header(unauthorized_hr),
        )
        assert r_unauth.status_code == 403

    # 3. Trạng thái không hợp lệ -> 422, không tạo notification
    r_invalid = isolated_client.patch(
        f"/api/v1/applications/{app_id}/status",
        json={"pipeline_status": "OFFER_SENT"},
        headers=_auth_header(ctx["hr_owner"]),
    )
    assert r_invalid.status_code == 422
    assert (
        isolated_client.get(
            "/api/v1/notifications", headers=_auth_header(ctx["cand_1"])
        ).json()
        == []
    )

    # 4. Chuyển sang INTERVIEW nhưng thiếu interview_schedule -> 422
    r_missing_sched = isolated_client.patch(
        f"/api/v1/applications/{app_id}/status",
        json={"pipeline_status": "INTERVIEW"},
        headers=_auth_header(ctx["hr_owner"]),
    )
    assert r_missing_sched.status_code == 422

    # 5. HR sở hữu job chuyển APPLIED -> SCREENING kèm recruiter_note -> 200
    r_screen = isolated_client.patch(
        f"/api/v1/applications/{app_id}/status",
        json={"pipeline_status": "SCREENING", "recruiter_note": "CV rất tiềm năng"},
        headers=_auth_header(ctx["hr_owner"]),
    )
    assert r_screen.status_code == 200, r_screen.text
    body_screen = r_screen.json()
    assert body_screen["pipeline_status"] == "SCREENING"
    assert body_screen["recruiter_note"] == "CV rất tiềm năng"
    assert [h["status"] for h in body_screen["status_history"]] == ["APPLIED", "SCREENING"]
    assert body_screen["status_history"][-1]["changed_by"] == str(ctx["hr_owner"].id)
    assert body_screen["status_history"][-1]["time"].endswith("Z")
    assert len(sent_emails) == 1
    assert sent_emails[0][0] == "cand1@example.com"

    # 6. Chuyển SCREENING -> INTERVIEW kèm interview_schedule -> lưu lịch + thêm lịch sử + tạo notification
    r_interview = isolated_client.patch(
        f"/api/v1/applications/{app_id}/status",
        json={
            "pipeline_status": "INTERVIEW",
            "interview_schedule": {
                "time": "2026-12-05T09:30:00",
                "location": "Tầng 8, Tòa nhà Alpha",
                "link": "https://meet.google.com/abc-defg-hij",
            },
        },
        headers=_auth_header(ctx["hr_owner"]),
    )
    assert r_interview.status_code == 200, r_interview.text
    body_int = r_interview.json()
    assert body_int["pipeline_status"] == "INTERVIEW"
    assert body_int["interview_schedule"]["location"] == "Tầng 8, Tòa nhà Alpha"
    assert body_int["interview_schedule"]["link"] == "https://meet.google.com/abc-defg-hij"
    assert [h["status"] for h in body_int["status_history"]] == [
        "APPLIED",
        "SCREENING",
        "INTERVIEW",
    ]
    assert len(sent_emails) == 2

    # 7. Gửi lại y hệt trạng thái + lịch phỏng vấn (chỉ sửa recruiter_note) -> KHÔNG tạo notification/email trùng
    r_same = isolated_client.patch(
        f"/api/v1/applications/{app_id}/status",
        json={
            "pipeline_status": "INTERVIEW",
            "recruiter_note": "Đã xác nhận hội đồng phỏng vấn",
            "interview_schedule": {
                "time": "2026-12-05T09:30:00",
                "location": "Tầng 8, Tòa nhà Alpha",
                "link": "https://meet.google.com/abc-defg-hij",
            },
        },
        headers=_auth_header(ctx["hr_owner"]),
    )
    assert r_same.status_code == 200
    assert len(r_same.json()["status_history"]) == 3  # không bị ghi trùng
    assert len(sent_emails) == 2                      # không gửi email trùng

    # 8. Kiểm tra GET /api/v1/notifications & PATCH /api/v1/notifications/{id}/read
    notifs = isolated_client.get(
        "/api/v1/notifications", headers=_auth_header(ctx["cand_1"])
    ).json()
    assert len(notifs) == 2
    assert all(n["type"] == "APPLICATION_STATUS" for n in notifs)
    # Mới nhất đứng trước (INTERVIEW trước SCREENING)
    assert "Hẹn phỏng vấn" in notifs[0]["title"]
    assert "https://meet.google.com/abc-defg-hij" in notifs[0]["content"]
    assert "Đang sơ loại" in notifs[1]["title"]

    # User khác không thấy và không được đánh dấu đã đọc
    assert (
        isolated_client.get(
            "/api/v1/notifications", headers=_auth_header(ctx["cand_2"])
        ).json()
        == []
    )
    nid = notifs[0]["id"]
    assert (
        isolated_client.patch(
            f"/api/v1/notifications/{nid}/read", headers=_auth_header(ctx["cand_2"])
        ).status_code
        == 404
    )

    # Chủ sở hữu đánh dấu đã đọc thành công
    r_read = isolated_client.patch(
        f"/api/v1/notifications/{nid}/read", headers=_auth_header(ctx["cand_1"])
    )
    assert r_read.status_code == 200
    assert r_read.json()["is_read"] is True

    # 9. Lỗi trong tầng notification/SMTP KHÔNG làm hỏng trạng thái đơn đã lưu
    async def _broken_create(*_a, **_kw):
        raise RuntimeError("Simulated DB notification outage")

    monkeypatch.setattr(notification_service, "create_notification", _broken_create)
    r_hired = isolated_client.patch(
        f"/api/v1/applications/{app_id}/status",
        json={"pipeline_status": "HIRED"},
        headers=_auth_header(ctx["hr_owner"]),
    )
    assert r_hired.status_code == 200
    assert r_hired.json()["pipeline_status"] == "HIRED"
    assert [h["status"] for h in r_hired.json()["status_history"]] == [
        "APPLIED",
        "SCREENING",
        "INTERVIEW",
        "HIRED",
    ]


def test_task_9_3_smtp_loopback_and_failure_resilience(monkeypatch):
    """Kiểm chứng email_service với local loopback SMTP giả lập VÀ khi SMTP sập."""
    received_payloads: List[bytes] = []

    class _LoopbackSMTPHandler(socketserver.StreamRequestHandler):
        def handle(self):
            self.wfile.write(b"220 localhost ESMTP ready\r\n")
            in_data = False
            buf = bytearray()
            while True:
                line = self.rfile.readline()
                if not line:
                    break
                if in_data:
                    if line in (b".\r\n", b".\n"):
                        received_payloads.append(bytes(buf))
                        in_data = False
                        self.wfile.write(b"250 2.0.0 OK queued\r\n")
                    else:
                        buf.extend(line)
                    continue
                upper = line.upper()
                if upper.startswith((b"EHLO", b"HELO")):
                    self.wfile.write(b"250-localhost\r\n250 SIZE 10240000\r\n")
                elif upper.startswith((b"MAIL FROM", b"RCPT TO")):
                    self.wfile.write(b"250 2.1.0 OK\r\n")
                elif upper.startswith(b"DATA"):
                    in_data = True
                    self.wfile.write(b"354 End data with <CR><LF>.<CR><LF>\r\n")
                elif upper.startswith(b"QUIT"):
                    self.wfile.write(b"221 Bye\r\n")
                    break
                else:
                    self.wfile.write(b"250 OK\r\n")

    server = socketserver.TCPServer(("127.0.0.1", 0), _LoopbackSMTPHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        monkeypatch.setattr(settings, "SMTP_HOST", "127.0.0.1")
        monkeypatch.setattr(settings, "SMTP_PORT", port)
        monkeypatch.setattr(settings, "SMTP_FROM", "noreply@example.com")
        monkeypatch.setattr(settings, "SMTP_USER", "")
        monkeypatch.setattr(settings, "SMTP_PASSWORD", "")
        monkeypatch.setattr(settings, "SMTP_USE_TLS", False)
        monkeypatch.setattr(settings, "SMTP_TIMEOUT_SECONDS", 3.0)

        ok = email_service.send_email(
            "cand1@example.com",
            "Cập nhật đơn ứng tuyển: Hẹn phỏng vấn",
            "Xin chào Hùng, bạn có lịch phỏng vấn.",
            email_service.render_html("Hẹn phỏng vấn", ["Xin chào Hùng"], "http://localhost:5173"),
        )
        assert ok is True
        assert len(received_payloads) == 1
        assert b"cand1@example.com" in received_payloads[0]
    finally:
        server.shutdown()
        server.server_close()

    # Khi cổng SMTP không phản hồi -> trả False, ghi log, KHÔNG raise exception
    monkeypatch.setattr(settings, "SMTP_HOST", "127.0.0.1")
    monkeypatch.setattr(settings, "SMTP_PORT", 1)
    monkeypatch.setattr(settings, "SMTP_TIMEOUT_SECONDS", 0.5)
    assert email_service.send_email("cand1@example.com", "Test lỗi SMTP", "Nội dung") is False


# ==============================================================================
# TASK 9.2 (UC-C7): THEO DÕI ĐƠN ỨNG TUYỂN CỦA CANDIDATE
# ==============================================================================
def test_task_9_2_candidate_applications_isolation_and_soft_deleted_job(
    isolated_client: TestClient,
):
    ctx = _seed_base_entities(isolated_client)
    app_id = str(ctx["app_1"].id)

    # HR cập nhật sang INTERVIEW + ghi chú nội bộ
    isolated_client.patch(
        f"/api/v1/applications/{app_id}/status",
        json={
            "pipeline_status": "INTERVIEW",
            "recruiter_note": "Bí mật nội bộ HR",
            "interview_schedule": {
                "time": "2026-12-10T14:00:00",
                "location": "Phòng 302",
                "link": "https://meet.google.com/xyz-uvwx-rst",
            },
        },
        headers=_auth_header(ctx["hr_owner"]),
    )

    # 1. Candidate 1 có đơn ứng tuyển đầy đủ job, company, pipeline_status, status_history, interview_schedule
    r_me = isolated_client.get("/api/v1/applications/me", headers=_auth_header(ctx["cand_1"]))
    assert r_me.status_code == 200
    items = r_me.json()
    assert len(items) == 1
    item = items[0]
    assert item["job_title"] == "Senior FastAPI Engineer"
    assert item["company_name"] == "Alpha Tech Corp"
    assert item["job"]["title"] == "Senior FastAPI Engineer"
    assert item["company"]["name"] == "Alpha Tech Corp"
    assert item["pipeline_status"] == "INTERVIEW"
    assert [h["status"] for h in item["status_history"]] == ["APPLIED", "INTERVIEW"]
    assert item["interview_schedule"]["location"] == "Phòng 302"
    assert "recruiter_note" not in item  # Tuyệt đối không lộ ghi chú nội bộ cho ứng viên

    # Chi tiết đơn cho Candidate 1: recruiter_note phải là None
    r_detail = isolated_client.get(
        f"/api/v1/applications/{app_id}", headers=_auth_header(ctx["cand_1"])
    )
    assert r_detail.status_code == 200
    assert r_detail.json()["recruiter_note"] is None

    # 2. Candidate 2 chưa nộp đơn -> trả mảng rỗng & không truy cập được đơn của Candidate 1
    assert (
        isolated_client.get("/api/v1/applications/me", headers=_auth_header(ctx["cand_2"])).json()
        == []
    )
    assert (
        isolated_client.get(
            f"/api/v1/applications/{app_id}", headers=_auth_header(ctx["cand_2"])
        ).status_code
        == 404
    )

    # 3. Khi Admin xóa mềm job -> Candidate 1 vẫn xem được đơn và biết job đã bị gỡ (is_deleted=True)
    r_del = isolated_client.patch(
        f"/api/v1/admin/jobs/{ctx['job_1'].id}/status",
        json={"status": "DELETED"},
        headers=_auth_header(ctx["admin"]),
    )
    assert r_del.status_code == 200

    r_after = isolated_client.get("/api/v1/applications/me", headers=_auth_header(ctx["cand_1"]))
    assert r_after.status_code == 200
    after_item = r_after.json()[0]
    assert after_item["job"]["is_deleted"] is True
    assert after_item["job_title"] == "Senior FastAPI Engineer"


# ==============================================================================
# TASK 10.1 (NAM & HƯỞNG): ADMIN MODERATION & STATISTICS (UC-A1..UC-A4)
# ==============================================================================
def test_task_10_1_admin_moderation_and_statistics_with_real_mongodb(
    isolated_client: TestClient,
):
    # Kiểm tra collection rỗng trước khi seed
    async def _seed_only_admin():
        adm = User(
            email="empty.admin@example.com",
            password_hash=hash_password("Admin123!"),
            full_name="Only Admin",
            role="ADMIN",
        )
        await adm.insert()
        return adm

    only_admin = isolated_client.portal.call(_seed_only_admin)
    r_empty_stats = isolated_client.get(
        "/api/v1/admin/statistics", headers=_auth_header(only_admin)
    )
    assert r_empty_stats.status_code == 200
    empty_data = r_empty_stats.json()
    assert empty_data["companies"]["total"] == 0
    assert empty_data["jobs"]["total"] == 0
    assert empty_data["applications"]["total"] == 0
    assert empty_data["ai_matching"]["average_score"] == 0.0

    # Seed dữ liệu đầy đủ
    ctx = _seed_base_entities(isolated_client)

    # Thêm các application đa dạng khoảng điểm (<50, 50-75, >75, None) để kiểm chứng UC-A4
    async def _seed_extra_apps():
        app_low = Application(
            job_id=ctx["job_2"].id,
            candidate_id=ctx["cand_1"].id,
            cv_url="/low.pdf",
            pipeline_status="REJECTED",
            ai_match_score=42.0,
            matching_version="v1.0",
            ai_status="DONE",
        )
        app_mid = Application(
            job_id=ctx["job_1"].id,
            candidate_id=ctx["cand_2"].id,
            cv_url="/mid.pdf",
            pipeline_status="SCREENING",
            ai_match_score=65.5,
            matching_version="v2.0",
            ai_status="DONE",
        )
        app_null = Application(
            job_id=ctx["job_2"].id,
            candidate_id=ctx["cand_2"].id,
            cv_url="/null.pdf",
            pipeline_status="APPLIED",
            ai_match_score=None,
            matching_version="v2.0",
            ai_status="FAILED",
        )
        for doc in (app_low, app_mid, app_null):
            await doc.insert()

    isolated_client.portal.call(_seed_extra_apps)

    # Phân quyền RBAC: Candidate & Recruiter bị từ chối 403 trên mọi route Admin
    for non_admin in (ctx["cand_1"], ctx["hr_owner"]):
        assert (
            isolated_client.get("/api/v1/admin/users", headers=_auth_header(non_admin)).status_code
            == 403
        )
        assert (
            isolated_client.get(
                "/api/v1/admin/statistics", headers=_auth_header(non_admin)
            ).status_code
            == 403
        )

    admin_hdr = _auth_header(ctx["admin"])

    # UC-A1: Lọc & tìm kiếm user + Ban/Unban + Chặn tự khóa chính mình
    r_search = isolated_client.get("/api/v1/admin/users?q=Hùng&user_type=CANDIDATE", headers=admin_hdr)
    assert r_search.status_code == 200
    assert r_search.json()["total"] == 1
    assert r_search.json()["items"][0]["email"] == "cand1@example.com"

    assert (
        isolated_client.patch(
            f"/api/v1/admin/users/{ctx['admin'].id}/status",
            json={"status": "BANNED"},
            headers=admin_hdr,
        ).status_code
        == 409
    )

    r_ban = isolated_client.patch(
        f"/api/v1/admin/users/{ctx['cand_2'].id}/status",
        json={"status": "BANNED"},
        headers=admin_hdr,
    )
    assert r_ban.status_code == 200 and r_ban.json()["status"] == "BANNED"
    # User bị khóa không thể gọi API cần đăng nhập -> 403
    assert (
        isolated_client.get("/api/v1/applications/me", headers=_auth_header(ctx["cand_2"])).status_code
        == 403
    )
    # Unban lại thành ACTIVE
    r_unban = isolated_client.patch(
        f"/api/v1/admin/users/{ctx['cand_2'].id}/status",
        json={"status": "ACTIVE"},
        headers=admin_hdr,
    )
    assert r_unban.status_code == 200 and r_unban.json()["status"] == "ACTIVE"

    # UC-A2: Lọc PENDING, tìm kiếm q & Duyệt/Reject công ty (bảo đảm tương thích cả khi có/không có q)
    assert isolated_client.get("/api/v1/admin/companies", headers=admin_hdr).json()["total"] == 2
    assert (
        isolated_client.get("/api/v1/admin/companies?q=Beta", headers=admin_hdr).json()["total"]
        == 1
    )
    r_pending_co = isolated_client.get(
        "/api/v1/admin/companies?verification_status=PENDING", headers=admin_hdr
    )
    assert r_pending_co.json()["total"] == 1
    r_verify = isolated_client.patch(
        f"/api/v1/admin/companies/{ctx['comp_b'].id}/verify",
        json={"verification_status": "REJECTED"},
        headers=admin_hdr,
    )
    assert r_verify.status_code == 200 and r_verify.json()["verification_status"] == "REJECTED"

    # UC-A3: Lọc/tìm kiếm jobs (có & không có q), Ẩn job (HIDDEN) -> biến mất khỏi tìm kiếm công khai nhưng không mất application
    assert isolated_client.get("/api/v1/admin/jobs", headers=admin_hdr).json()["total"] == 2
    assert (
        isolated_client.get("/api/v1/admin/jobs?q=FastAPI", headers=admin_hdr).json()["total"]
        == 1
    )
    assert isolated_client.get("/api/v1/jobs").json()["total"] == 1
    r_hide = isolated_client.patch(
        f"/api/v1/admin/jobs/{ctx['job_1'].id}/status",
        json={"status": "HIDDEN"},
        headers=admin_hdr,
    )
    assert r_hide.status_code == 200 and r_hide.json()["status"] == "HIDDEN"
    assert isolated_client.get("/api/v1/jobs").json()["total"] == 0

    # UC-A4: Đối chiếu thống kê thực tế với dữ liệu MongoDB
    stats = isolated_client.get("/api/v1/admin/statistics", headers=admin_hdr).json()
    assert stats["users"]["candidates"] == 2
    assert stats["users"]["recruiters"] == 3
    assert stats["companies"]["verified"] == 1
    assert stats["companies"]["rejected"] == 1
    assert stats["jobs"]["hidden"] == 1
    assert stats["jobs"]["closed"] == 1
    assert stats["applications"]["total"] == 4
    assert stats["applications"]["by_pipeline_status"] == {
        "APPLIED": 2,
        "SCREENING": 1,
        "INTERVIEW": 0,
        "HIRED": 0,
        "REJECTED": 1,
    }
    # Điểm hợp lệ: 84.5 (>75), 42.0 (<50), 65.5 (50-75) -> trung bình = (84.5 + 42.0 + 65.5)/3 = 64.0
    assert stats["ai_matching"]["total_scored"] == 3
    assert stats["ai_matching"]["average_score"] == 64.0
    assert stats["ai_matching"]["score_distribution"]["under_50"] == 1
    assert stats["ai_matching"]["score_distribution"]["from_50_to_75"] == 1
    assert stats["ai_matching"]["score_distribution"]["over_75"] == 1
    assert stats["ai_matching"]["by_matching_version"] == {"v1.0": 2, "v2.0": 2}


# ==============================================================================
# TASK 10.3 & UC-R7: CHAT REST API + WEBSOCKET REALTIME 2 CLIENT
# ==============================================================================
def test_task_10_3_chat_rest_and_realtime_websocket(monkeypatch):
    """Chạy Uvicorn thật trên cổng động (127.0.0.1:0) + 2 kết nối websockets độc lập
    để tránh xung đột 2 event loop của Starlette TestClient.websocket_connect với Motor."""
    import asyncio
    import json
    import socket
    import httpx
    import uvicorn
    import websockets
    from websockets.exceptions import ConnectionClosed

    monkeypatch.setattr(db_module, "MONGO_URI", TEST_DB_URI)
    monkeypatch.setattr(settings, "SMTP_HOST", "")

    async def _run_scenario():
        await _drop_isolated_db()

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

        config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", lifespan="on")
        server = uvicorn.Server(config)
        server_task = asyncio.create_task(server.serve(sockets=[sock]))
        try:
            while not server.started:
                await asyncio.sleep(0.05)

            # Seed dữ liệu trực tiếp trên cùng event loop với Uvicorn & Motor
            comp_a = Company(name="Alpha Tech Corp", verification_status="VERIFIED")
            comp_b = Company(name="Beta Data Ltd", verification_status="PENDING")
            await comp_a.insert()
            await comp_b.insert()

            hr_owner = User(
                email="hr.owner@example.com",
                password_hash=hash_password("Hr123456!"),
                full_name="HR Mạnh",
                user_type="RECRUITER",
                company_id=comp_a.id,
            )
            hr_other_co = User(
                email="hr.other@example.com",
                password_hash=hash_password("Hr123456!"),
                full_name="HR Công Ty Khác",
                user_type="RECRUITER",
                company_id=comp_b.id,
            )
            cand_1 = User(
                email="cand1@example.com",
                password_hash=hash_password("Cand1234!"),
                full_name="Ứng viên Hùng",
                user_type="CANDIDATE",
            )
            cand_2 = User(
                email="cand2@example.com",
                password_hash=hash_password("Cand1234!"),
                full_name="Ứng viên Nam",
                user_type="CANDIDATE",
            )
            for u in (hr_owner, hr_other_co, cand_1, cand_2):
                await u.insert()

            job_1 = JobPosting(
                company_id=comp_a.id,
                recruiter_id=hr_owner.id,
                title="Senior FastAPI Engineer",
                description="FastAPI & MongoDB",
                status="OPEN",
            )
            await job_1.insert()

            app_1 = Application(
                job_id=job_1.id,
                candidate_id=cand_1.id,
                cv_url=f"/uploads/cvs/{cand_1.id}/sample.pdf",
                pipeline_status="APPLIED",
            )
            await app_1.insert()

            job_id = str(job_1.id)
            cand1_id = str(cand_1.id)
            cand2_id = str(cand_2.id)
            base_http = f"http://127.0.0.1:{port}"
            base_ws = f"ws://127.0.0.1:{port}"

            async with httpx.AsyncClient(base_url=base_http, timeout=10.0) as http:
                # 1. HR không sở hữu job / candidate chưa nộp đơn / candidate mạo danh -> 403
                assert (
                    await http.post(
                        "/api/v1/conversations",
                        json={"job_id": job_id, "candidate_id": cand1_id},
                        headers=_auth_header(hr_other_co),
                    )
                ).status_code == 403
                assert (
                    await http.post(
                        "/api/v1/conversations",
                        json={"job_id": job_id, "candidate_id": cand2_id},
                        headers=_auth_header(hr_owner),
                    )
                ).status_code == 403
                assert (
                    await http.post(
                        "/api/v1/conversations",
                        json={"job_id": job_id, "candidate_id": cand2_id},
                        headers=_auth_header(cand_1),
                    )
                ).status_code == 403

                # 2. HR tạo hội thoại mới -> gọi lại trả đúng hội thoại cũ (không tạo trùng)
                r_create = await http.post(
                    "/api/v1/conversations",
                    json={"job_id": job_id, "candidate_id": cand1_id},
                    headers=_auth_header(hr_owner),
                )
                assert r_create.status_code == 200, r_create.text
                conv = r_create.json()
                conv_id = conv["id"]
                assert conv["other_user"]["full_name"] == "Ứng viên Hùng"
                assert conv["job_title"] == "Senior FastAPI Engineer"

                r_again = await http.post(
                    "/api/v1/conversations",
                    json={"job_id": job_id, "candidate_id": cand1_id},
                    headers=_auth_header(hr_owner),
                )
                assert r_again.status_code == 200 and r_again.json()["id"] == conv_id

                r_cand_conv = await http.post(
                    "/api/v1/conversations",
                    json={"job_id": job_id},
                    headers=_auth_header(cand_1),
                )
                assert r_cand_conv.status_code == 200 and r_cand_conv.json()["id"] == conv_id
                assert r_cand_conv.json()["other_user"]["full_name"] == "HR Mạnh"

                # 3. Từ chối kết nối WebSocket khi JWT sai (4401) hoặc user ngoài hội thoại (4404)
                for bad_token, expected_code in [
                    ("invalid.jwt.token", 4401),
                    (_raw_token(cand_2), 4404),
                ]:
                    async with websockets.connect(
                        f"{base_ws}/ws/chat/{conv_id}?token={bad_token}"
                    ) as bad_ws:
                        with pytest.raises(ConnectionClosed) as exc_info:
                            await asyncio.wait_for(bad_ws.recv(), timeout=5.0)
                        assert exc_info.value.rcvd.code == expected_code

                # 4. Hai client (HR và Candidate) kết nối đồng thời, gửi & nhận realtime, lưu MongoDB
                old_updated_at = conv["updated_at"]
                async with websockets.connect(
                    f"{base_ws}/ws/chat/{conv_id}?token={_raw_token(hr_owner)}"
                ) as ws_hr, websockets.connect(
                    f"{base_ws}/ws/chat/{conv_id}?token={_raw_token(cand_1)}"
                ) as ws_cand:
                    await ws_hr.send(
                        json.dumps(
                            {
                                "event": "message",
                                "message_type": "TEXT",
                                "content": "Chào Hùng, mời bạn trao đổi thêm!",
                            }
                        )
                    )
                    ev_hr_1 = json.loads(await asyncio.wait_for(ws_hr.recv(), timeout=5.0))
                    ev_cand_1 = json.loads(await asyncio.wait_for(ws_cand.recv(), timeout=5.0))
                    assert ev_hr_1["event"] == "message"
                    assert ev_hr_1 == ev_cand_1
                    assert ev_cand_1["data"]["content"] == "Chào Hùng, mời bạn trao đổi thêm!"
                    assert ev_cand_1["data"]["sender_role"] == "RECRUITER"

                    await ws_cand.send(
                        json.dumps(
                            {
                                "event": "message",
                                "message_type": "TEXT",
                                "content": "Dạ em chào anh Mạnh ạ!",
                            }
                        )
                    )
                    ev_hr_2 = json.loads(await asyncio.wait_for(ws_hr.recv(), timeout=5.0))
                    ev_cand_2 = json.loads(await asyncio.wait_for(ws_cand.recv(), timeout=5.0))
                    assert ev_hr_2 == ev_cand_2
                    assert ev_hr_2["data"]["content"] == "Dạ em chào anh Mạnh ạ!"
                    assert ev_hr_2["data"]["sender_role"] == "CANDIDATE"

                # 5. Sau khi disconnect & reconnect: kiểm tra last_message, updated_at và lịch sử trong MongoDB
                convs_hr = (
                    await http.get("/api/v1/conversations", headers=_auth_header(hr_owner))
                ).json()
                assert len(convs_hr) == 1
                assert convs_hr[0]["last_message"] == "Dạ em chào anh Mạnh ạ!"
                assert convs_hr[0]["updated_at"] >= old_updated_at

                assert (
                    await http.get(
                        f"/api/v1/conversations/{conv_id}/messages",
                        headers=_auth_header(cand_2),
                    )
                ).status_code == 404

                history = (
                    await http.get(
                        f"/api/v1/conversations/{conv_id}/messages",
                        headers=_auth_header(cand_1),
                    )
                ).json()
                assert [m["content"] for m in history] == [
                    "Chào Hùng, mời bạn trao đổi thêm!",
                    "Dạ em chào anh Mạnh ạ!",
                ]
        finally:
            server.should_exit = True
            await server_task
            sock.close()
            await _drop_isolated_db()

    asyncio.run(_run_scenario())
