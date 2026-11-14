import re
from datetime import datetime, timezone
from typing import Literal

from beanie import PydanticObjectId
from beanie.odm.queries.update import UpdateResponse
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.deps import get_current_admin
from app.models.company import Company
from app.models.job import JobPosting
from app.models.user import User
from app.schemas.admin import (
    AdminCompanyItem,
    AdminCompanyVerificationUpdate,
    AdminJobItem,
    AdminJobStatusUpdate,
    AdminPage,
    AdminStatisticsResponse,
    AdminUserItem,
    AdminUserStatusUpdate,
)
from app.services import admin_service

router = APIRouter(dependencies=[Depends(get_current_admin)])


@router.get(
    "/statistics",
    response_model=AdminStatisticsResponse,
    summary="Thống kê tổng hợp hệ thống cho Admin (UC-A4 - Task 10.1)",
)
async def get_admin_statistics():
    return await admin_service.get_system_statistics()


async def _list_page(model, filters: dict, page: int, limit: int):
    total = await model.find(filters).count()
    items = await model.find(filters).sort("-_id").skip((page - 1) * limit).limit(limit).to_list()
    return {"items": items, "total": total, "page": page, "limit": limit}


async def _update_record(model, record_id: PydanticObjectId, changes: dict, not_found: str):
    updated = await model.find_one({"_id": record_id, "deleted_at": None}).update(
        {"$set": {**changes, "updated_at": datetime.now(timezone.utc)}},
        response_type=UpdateResponse.NEW_DOCUMENT,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail=not_found)
    return updated


@router.get("/users", response_model=AdminPage[AdminUserItem])
async def list_users(
    q: str = Query("", max_length=254),
    role: Literal["USER", "ADMIN"] | None = None,
    user_type: Literal["CANDIDATE", "RECRUITER"] | None = None,
    status: Literal["ACTIVE", "BANNED"] | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    filters = {"deleted_at": None}
    if q.strip():
        term = {"$regex": re.escape(q.strip()), "$options": "i"}
        filters["$or"] = [{"full_name": term}, {"email": term}]
    selected = {"role": role, "user_type": user_type, "status": status}
    filters.update({key: value for key, value in selected.items() if value is not None})
    return await _list_page(User, filters, page, limit)


@router.patch("/users/{user_id}/status", response_model=AdminUserItem)
async def update_user_status(
    user_id: PydanticObjectId,
    payload: AdminUserStatusUpdate,
    admin: User = Depends(get_current_admin),
):
    if user_id == admin.id and payload.status == "BANNED":
        raise HTTPException(status_code=409, detail="Bạn không thể khóa tài khoản đang sử dụng.")
    return await _update_record(User, user_id, payload.model_dump(), "Không tìm thấy tài khoản.")


@router.get("/companies", response_model=AdminPage[AdminCompanyItem])
async def list_companies(
    verification_status: Literal["PENDING", "VERIFIED", "REJECTED"] | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    filters = {"deleted_at": None}
    if verification_status is not None:
        filters["verification_status"] = verification_status
    return await _list_page(Company, filters, page, limit)


@router.patch("/companies/{company_id}/verify", response_model=AdminCompanyItem)
async def verify_company(company_id: PydanticObjectId, payload: AdminCompanyVerificationUpdate):
    return await _update_record(Company, company_id, payload.model_dump(), "Không tìm thấy doanh nghiệp.")


@router.get("/jobs", response_model=AdminPage[AdminJobItem])
async def list_jobs(
    status: Literal["OPEN", "CLOSED", "HIDDEN"] | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    filters = {"deleted_at": None}
    if status is not None:
        filters["status"] = status
    result = await _list_page(JobPosting, filters, page, limit)
    jobs = result["items"]
    company_ids = list({job.company_id for job in jobs})
    companies = []
    if company_ids:
        companies = await Company.find({"_id": {"$in": company_ids}, "deleted_at": None}).to_list()
    names = {company.id: company.name for company in companies}
    result["items"] = [
        AdminJobItem.model_validate(job).model_copy(update={"company_name": names.get(job.company_id)})
        for job in jobs
    ]
    return result


@router.patch("/jobs/{job_id}/status", response_model=AdminJobItem)
async def moderate_job(job_id: PydanticObjectId, payload: AdminJobStatusUpdate):
    changes = {"status": "HIDDEN"}
    if payload.status == "DELETED":
        changes["deleted_at"] = datetime.now(timezone.utc)
    return await _update_record(JobPosting, job_id, changes, "Không tìm thấy tin tuyển dụng.")
