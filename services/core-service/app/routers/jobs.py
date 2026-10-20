from fastapi import APIRouter, Depends, HTTPException, status
from app.core.deps import get_current_user  
from app.schemas.job import JobCreateSchema, JobUpdateSchema, JobStatusUpdateSchema
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