from fastapi import APIRouter, Depends, HTTPException, status
from app.core.deps import get_current_user  
from app.schemas.job import JobCreateSchema, JobUpdateSchema, JobStatusUpdateSchema
from app.services.job_service import JobService
from app.models.company import Company
from app.models.job import JobPosting
from app.models.skill import SkillsTaxonomy

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


async def serialize_job(job: JobPosting):
    company = await Company.get(job.company_id)
    skills = await SkillsTaxonomy.find(
        {"_id": {"$in": job.required_skills}}
    ).to_list() if job.required_skills else []
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
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


@router.get("/mine")
async def list_my_jobs(current_user=Depends(get_current_recruiter)):
    jobs = await JobPosting.find(
        {"recruiter_id": current_user.id, "deleted_at": None}
    ).to_list()
    jobs.sort(key=lambda job: job.created_at, reverse=True)
    return {"data": [await serialize_job(job) for job in jobs]}


@router.get("")
async def list_public_jobs():
    jobs = await JobPosting.find(
        {"status": "OPEN", "deleted_at": None}
    ).to_list()
    jobs.sort(key=lambda job: job.created_at, reverse=True)
    return {"data": [await serialize_job(job) for job in jobs]}


@router.get("/{job_id}")
async def get_public_job(job_id: str):
    job = await JobPosting.get(job_id)
    if not job or job.deleted_at is not None or job.status != "OPEN":
        raise HTTPException(status_code=404, detail="Không tìm thấy tin tuyển dụng")
    return await serialize_job(job)


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
    job = await JobService.update_job_with_embedding(job_id, job_in, current_user)
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
    result = await JobService.update_status(job_id, status_in, current_user)
    return result