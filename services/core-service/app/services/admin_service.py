import math
from typing import Dict

from app.models.application import Application
from app.models.company import Company
from app.models.job import JobPosting
from app.models.user import User
from app.schemas.admin import (
    AIMatchingStatistics,
    AdminStatisticsResponse,
    ApplicationStatistics,
    CompanyStatistics,
    JobStatistics,
    UserStatistics,
)


async def get_system_statistics() -> AdminStatisticsResponse:
    """Tổng hợp số liệu hệ thống cho Admin Dashboard (UC-A4 - Task 10.1)."""
    users = await User.find({"deleted_at": None}).to_list()
    companies = await Company.find({"deleted_at": None}).to_list()
    jobs = await JobPosting.find({"deleted_at": None}).to_list()
    applications = await Application.find_all().to_list()

    # 1. Thống kê người dùng (bỏ qua bản ghi xóa mềm)
    candidates = sum(1 for u in users if getattr(u, "user_type", None) == "CANDIDATE")
    recruiters = sum(1 for u in users if getattr(u, "user_type", None) == "RECRUITER")
    admins = sum(1 for u in users if getattr(u, "role", None) == "ADMIN")
    active_users = sum(1 for u in users if getattr(u, "status", "ACTIVE") == "ACTIVE")
    banned_users = sum(1 for u in users if getattr(u, "status", None) == "BANNED")

    user_stats = UserStatistics(
        total=len(users),
        candidates=candidates,
        recruiters=recruiters,
        admins=admins,
        active=active_users,
        banned=banned_users,
        by_user_type={
            "CANDIDATE": candidates,
            "RECRUITER": recruiters,
            "ADMIN": admins,
        },
        by_status={
            "ACTIVE": active_users,
            "BANNED": banned_users,
        },
    )

    # 2. Thống kê công ty (bỏ qua bản ghi xóa mềm)
    pending_companies = sum(
        1 for c in companies if getattr(c, "verification_status", None) == "PENDING"
    )
    verified_companies = sum(
        1 for c in companies if getattr(c, "verification_status", None) == "VERIFIED"
    )
    rejected_companies = sum(
        1 for c in companies if getattr(c, "verification_status", None) == "REJECTED"
    )

    company_stats = CompanyStatistics(
        total=len(companies),
        pending=pending_companies,
        verified=verified_companies,
        rejected=rejected_companies,
        by_verification_status={
            "PENDING": pending_companies,
            "VERIFIED": verified_companies,
            "REJECTED": rejected_companies,
        },
    )

    # 3. Thống kê tin tuyển dụng (bỏ qua bản ghi xóa mềm)
    open_jobs = sum(1 for j in jobs if getattr(j, "status", None) == "OPEN")
    closed_jobs = sum(1 for j in jobs if getattr(j, "status", None) == "CLOSED")
    hidden_jobs = sum(1 for j in jobs if getattr(j, "status", None) == "HIDDEN")

    job_stats = JobStatistics(
        total=len(jobs),
        open=open_jobs,
        closed=closed_jobs,
        hidden=hidden_jobs,
        by_status={
            "OPEN": open_jobs,
            "CLOSED": closed_jobs,
            "HIDDEN": hidden_jobs,
        },
    )

    # 4. Thống kê đơn ứng tuyển theo pipeline_status
    pipeline_counts: Dict[str, int] = {
        "APPLIED": 0,
        "SCREENING": 0,
        "INTERVIEW": 0,
        "HIRED": 0,
        "REJECTED": 0,
    }
    for app in applications:
        st = getattr(app, "pipeline_status", None) or "APPLIED"
        pipeline_counts[st] = pipeline_counts.get(st, 0) + 1

    application_stats = ApplicationStatistics(
        total=len(applications),
        applied=pipeline_counts.get("APPLIED", 0),
        screening=pipeline_counts.get("SCREENING", 0),
        interview=pipeline_counts.get("INTERVIEW", 0),
        hired=pipeline_counts.get("HIRED", 0),
        rejected=pipeline_counts.get("REJECTED", 0),
        by_pipeline_status=pipeline_counts,
    )

    # 5. Thống kê kết quả AI Matching
    valid_scores: list[float] = []
    under_50 = 0
    from_50_to_75 = 0
    over_75 = 0
    by_version: Dict[str, int] = {}
    by_ai_status: Dict[str, int] = {
        "DONE": 0,
        "FAILED": 0,
        "PENDING": 0,
        "PROCESSING": 0,
        "SKIPPED": 0,
    }

    for app in applications:
        raw_score = getattr(app, "ai_match_score", None)
        has_valid_score = (
            isinstance(raw_score, (int, float))
            and not isinstance(raw_score, bool)
            and math.isfinite(float(raw_score))
        )
        if has_valid_score:
            score = max(0.0, min(100.0, float(raw_score)))
            valid_scores.append(score)
            if score < 50.0:
                under_50 += 1
            elif score <= 75.0:
                from_50_to_75 += 1
            else:
                over_75 += 1

        version = getattr(app, "matching_version", None)
        if version:
            by_version[str(version)] = by_version.get(str(version), 0) + 1

        raw_ai_status = getattr(app, "ai_status", None)
        if raw_ai_status == "COMPLETED":
            normalized_ai_status = "DONE"
        elif raw_ai_status in by_ai_status:
            normalized_ai_status = raw_ai_status
        else:
            normalized_ai_status = "DONE" if has_valid_score else "FAILED"
        by_ai_status[normalized_ai_status] = by_ai_status.get(normalized_ai_status, 0) + 1

    avg_score = round(sum(valid_scores) / len(valid_scores), 2) if valid_scores else 0.0

    ai_stats = AIMatchingStatistics(
        total_scored=len(valid_scores),
        average_score=avg_score,
        score_distribution={
            "under_50": under_50,
            "from_50_to_75": from_50_to_75,
            "over_75": over_75,
            "<50%": under_50,
            "50-75%": from_50_to_75,
            ">75%": over_75,
        },
        by_matching_version=by_version,
        by_ai_status=by_ai_status,
    )

    return AdminStatisticsResponse(
        users=user_stats,
        companies=company_stats,
        jobs=job_stats,
        applications=application_stats,
        ai_matching=ai_stats,
    )
