import re
from datetime import datetime
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.deps import get_current_user
from app.models.job import JobPosting
from app.schemas.job import (
    JobCreateSchema,
    JobUpdateSchema,
    JobStatusUpdateSchema,
)
from app.services.job_service import JobService

router = APIRouter(tags=["Jobs"])

async def get_current_recruiter(current_user = Depends(get_current_user)):
    # Kiểm tra role của user có phải là RECRUITER không
    user_role = getattr(current_user, "user_type", None)
    if user_role != "RECRUITER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ tài khoản Nhà tuyển dụng (Recruiter) mới có quyền thực hiện thao tác này"
        )
    return current_user
@router.post("", status_code=status.HTTP_201_CREATED)
async def create_job(
    job_in: JobCreateSchema,
    current_user = Depends(get_current_recruiter)
):
    job = await JobService.create_job(job_in, current_user)
    return {
        "message": "Đăng tin tuyển dụng thành công!",
        "data": job
    }

@router.put("/{job_id}")
async def update_job(
    job_id: str,
    job_in: JobUpdateSchema,
    current_user = Depends(get_current_recruiter)
):
    updated_job = await JobService.update_job(job_id, job_in, current_user)
    return updated_job

@router.patch("/{job_id}/status")
async def update_job_status(
    job_id: str,
    status_in: JobStatusUpdateSchema,
    current_user = Depends(get_current_recruiter)
):
    result = await JobService.update_status(job_id, status_in, current_user)
    return result
def _serialize_candidate_job(doc: dict) -> dict:
    """Chuyển tài liệu MongoDB thành JSON cho giao diện ứng viên."""
    company = doc.pop("company", None)

    doc["id"] = str(doc.pop("_id"))

    for field in ("company_id", "recruiter_id"):
        if doc.get(field) is not None:
            doc[field] = str(doc[field])

    doc["required_skills"] = [
        str(skill) for skill in doc.get("required_skills", [])
    ]

    doc["company_name"] = company.get("name", "") if company else ""

    if company:
        doc["company"] = {
            "id": str(company["_id"]),
            "name": company.get("name"),
            "logo_url": company.get("logo_url"),
            "industry": company.get("industry"),
            "address": company.get("address"),
        }
    else:
        doc["company"] = None

    # Không gửi vector nội bộ của AI sang frontend.
    doc.pop("job_embedding_vector", None)
    doc.pop("embedding_model", None)

    for field in ("created_at", "updated_at", "deleted_at"):
        value = doc.get(field)
        if isinstance(value, datetime):
            doc[field] = value.isoformat()

    return doc


@router.get("", summary="Tìm kiếm việc làm cho ứng viên")
async def search_jobs(
    keyword: Optional[str] = Query(None, max_length=100),
    location: Optional[str] = Query(None, max_length=100),
    level: Optional[str] = Query(None, max_length=30),
    salary_min: Optional[float] = Query(None, ge=0),
    salary_max: Optional[float] = Query(None, ge=0),
    page: int = Query(1, ge=1),
    limit: int = Query(6, ge=1, le=100),
):
    if (
        salary_min is not None
        and salary_max is not None
        and salary_min > salary_max
    ):
        raise HTTPException(
            status_code=400,
            detail="Lương tối thiểu không được lớn hơn lương tối đa.",
        )

    # Bắt buộc chỉ lấy việc đang tuyển, chưa bị xóa mềm.
    pipeline = [
        {
            "$match": {
                "status": "OPEN",
                "deleted_at": None,
            }
        },
        {
            "$lookup": {
                "from": "companies",
                "localField": "company_id",
                "foreignField": "_id",
                "as": "company",
            }
        },
        {
            "$unwind": {
                "path": "$company",
                "preserveNullAndEmptyArrays": True,
            }
        },
    ]

    filters = {}

    if keyword and keyword.strip():
        pattern = re.escape(keyword.strip())
        filters["$or"] = [
            {"title": {"$regex": pattern, "$options": "i"}},
            {"description": {"$regex": pattern, "$options": "i"}},
            {"company.name": {"$regex": pattern, "$options": "i"}},
        ]

    if location and location.strip():
        filters["location"] = {
            "$regex": re.escape(location.strip()),
            "$options": "i",
        }

    if level and level.strip():
        filters["level"] = {
            "$regex": f"^{re.escape(level.strip())}$",
            "$options": "i",
        }

    # Khoảng lương người dùng tìm kiếm phải giao với khoảng lương tin đăng.
    if salary_min is not None:
        filters["salary.max"] = {"$gte": salary_min}

    if salary_max is not None:
        filters["salary.min"] = {"$lte": salary_max}

    if filters:
        pipeline.append({"$match": filters})

    collection = JobPosting.get_motor_collection()

    count_result = await collection.aggregate(
        pipeline + [{"$count": "total"}]
    ).to_list(length=1)

    total = count_result[0]["total"] if count_result else 0

    rows = await collection.aggregate(
        pipeline
        + [
            {"$sort": {"created_at": -1}},
            {"$skip": (page - 1) * limit},
            {"$limit": limit},
            {
                "$project": {
                    "job_embedding_vector": 0,
                    "embedding_model": 0,
                }
            },
        ]
    ).to_list(length=limit)

    return {
        "items": [_serialize_candidate_job(job) for job in rows],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/{job_id}", summary="Xem chi tiết việc làm cho ứng viên")
async def get_candidate_job_detail(job_id: str):
    try:
        object_id = ObjectId(job_id)
    except (InvalidId, TypeError):
        raise HTTPException(
            status_code=400,
            detail="Mã việc làm không hợp lệ.",
        )

    collection = JobPosting.get_motor_collection()

    rows = await collection.aggregate(
        [
            {
                "$match": {
                    "_id": object_id,
                    "status": "OPEN",
                    "deleted_at": None,
                }
            },
            {
                "$lookup": {
                    "from": "companies",
                    "localField": "company_id",
                    "foreignField": "_id",
                    "as": "company",
                }
            },
            {
                "$unwind": {
                    "path": "$company",
                    "preserveNullAndEmptyArrays": True,
                }
            },
            {
                "$project": {
                    "job_embedding_vector": 0,
                    "embedding_model": 0,
                }
            },
        ]
    ).to_list(length=1)

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy tin tuyển dụng đang mở.",
        )

    return _serialize_candidate_job(rows[0])