from typing import Optional

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.deps import get_current_candidate
from app.models.user import User
from app.schemas.application import ApplicationResponse
from app.services import application_service
from app.services.cv_utils import CVError

router = APIRouter()


@router.post("", response_model=ApplicationResponse, status_code=201,
             summary="Nộp hồ sơ ứng tuyển + AI chấm điểm CV-JD (UC-C5)")
async def apply_to_job(
    job_id: str = Form(..., description="_id của tin tuyển dụng"),
    file: Optional[UploadFile] = File(default=None, description="CV PDF; bỏ trống = dùng CV trong hồ sơ"),
    user: User = Depends(get_current_candidate),
):
    try:
        oid = PydanticObjectId(job_id)
    except Exception:
        raise HTTPException(422, "job_id không hợp lệ")
    try:
        return await application_service.apply_job(user, oid, file)
    except CVError as e:
        raise HTTPException(e.status_code, e.message)
