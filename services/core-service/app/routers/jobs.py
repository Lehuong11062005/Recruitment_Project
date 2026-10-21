import re
from datetime import datetime
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.deps import get_current_user
from app.models.company import Company
from app.models.job import JobPosting
from app.models.skill import SkillsTaxonomy
from app.schemas.job import (
    JobCreateSchema,
    JobStatusUpdateSchema,
    JobUpdateSchema,
)
from app.services.job_service import JobService


router = APIRouter(tags=["Jobs"])


async def get_current_recruiter(current_user=Depends(get_current_user)):
    """Chỉ cho phép tài khoản nhà tuyển dụng thực hiện thao tác quản lý tin."""
    user_role = getattr(current_user, "user_type", None)
    if user_role != "RECRUITER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ tài khoản Nhà tuyển dụng (Recruiter) mới có quyền thực hiện thao tác này",
        )
    return current_user


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


async def serialize_job(job: JobPosting) -> dict:
    """Chuẩn hóa tin tuyển dụng và bổ sung tên kỹ năng cho API quản lý."""
    company = await Company.get(job.company_id)
    skills = (
        await SkillsTaxonomy.find(
            {"_id": {"$in": job.required_skills}}
        ).to_list()
        if job.required_skills
        else []
    )

    return {
        "id": str(job.id),
        "title": job.title,
        "description": job.description,
        "company_id": str(job.company_id),
        "company_name": company.name if company else "Doanh nghiệp",
        "recruiter_id": str(job.recruiter_id),
        "required_skills": [str(skill_id) for skill_id in job.required_skills],
        "required_skill_names": [skill.name for skill in skills],
        "level": job.level,
        "experience_required": job.experience_required,
        "salary": job.salary,
        "location": job.location,
        "views_count": job.views_count,
        "applications_count": job.applications_count,
        "status": job.status,
        "created_at": (
            job.created_at.isoformat()
            if isinstance(job.created_at, datetime)
            else job.created_at
        ),
        "updated_at": (
            job.updated_at.isoformat()
            if isinstance(job.updated_at, datetime)
            else job.updated_at
        ),
    }


# ---------------------------------------------------------------------------
# Candidate/public APIs
# ---------------------------------------------------------------------------

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
    """Danh sách việc đang mở, có tìm kiếm, lọc và phân trang."""
    if (
        salary_min is not None
        and salary_max is not None
        and salary_min > salary_max
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lương tối thiểu không được lớn hơn lương tối đa.",
        )

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

    # Khoảng lương tìm kiếm phải giao với khoảng lương của tin đăng.
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


# Keep this static route before /{job_id} so "mine" is not treated as a job ID.
@router.get("/mine", summary="Danh sách tin tuyển dụng của tôi")
async def list_my_jobs(current_user=Depends(get_current_recruiter)):
    jobs = await JobPosting.find(
        {
            "recruiter_id": current_user.id,
            "deleted_at": None,
        }
    ).to_list()
    jobs.sort(key=lambda job: job.created_at or datetime.min, reverse=True)
    return {"data": [await serialize_job(job) for job in jobs]}


@router.get("/{job_id}", summary="Xem chi tiết việc làm đang tuyển")
async def get_candidate_job_detail(job_id: str):
    try:
        object_id = ObjectId(job_id)
    except (InvalidId, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tin tuyển dụng đang mở.",
        )

    return _serialize_candidate_job(rows[0])


# ---------------------------------------------------------------------------
# Recruiter APIs
# ---------------------------------------------------------------------------

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_job(
    job_in: JobCreateSchema,
    current_user=Depends(get_current_recruiter),
):
    job = await JobService.create_job(job_in, current_user)
    return {
        "message": "Đăng tin tuyển dụng thành công!",
        "data": job,
    }


@router.put("/{job_id}")
async def update_job(
    job_id: str,
    job_in: JobUpdateSchema,
    current_user=Depends(get_current_recruiter),
):
    updated_job = await JobService.update_job(job_id, job_in, current_user)
    return updated_job


@router.patch("/{job_id}/status")
async def update_job_status(
    job_id: str,
    status_in: JobStatusUpdateSchema,
    current_user=Depends(get_current_recruiter),
):
    return await JobService.update_status(job_id, status_in, current_user)


@router.post("/managed", status_code=status.HTTP_201_CREATED)
async def create_managed_job(
    job_in: JobCreateSchema,
    current_user=Depends(get_current_recruiter),
):
    if not getattr(current_user, "company_id", None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vui lòng cập nhật hồ sơ doanh nghiệp trước khi đăng tin",
        )

    await JobService.validate_required_skills(job_in.required_skills)
    job = await JobService.create_job_with_embedding(job_in, current_user)
    return {
        "message": "Đăng tin tuyển dụng thành công!",
        "data": await serialize_job(job),
    }


@router.put("/managed/{job_id}")
async def update_managed_job(
    job_id: str,
    job_in: JobUpdateSchema,
    current_user=Depends(get_current_recruiter),
):
    if job_in.required_skills is not None:
        await JobService.validate_required_skills(job_in.required_skills)

    job = await JobService.update_job_with_embedding(
        job_id, job_in, current_user
    )
    return await serialize_job(job)


@router.patch("/managed/{job_id}/status")
async def update_managed_job_status(
    job_id: str,
    status_in: JobStatusUpdateSchema,
    current_user=Depends(get_current_recruiter),
):
    if status_in.status not in {"OPEN", "CLOSED", "HIDDEN"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Trạng thái tin tuyển dụng phải là OPEN, CLOSED hoặc HIDDEN",
        )

    return await JobService.update_status(job_id, status_in, current_user)
