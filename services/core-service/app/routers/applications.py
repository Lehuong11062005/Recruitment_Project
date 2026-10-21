import json
from typing import List, Optional

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.deps import get_current_candidate
from app.models.user import User
from app.schemas.application import ApplicationResponse
from app.services import application_service
from app.services.cv_utils import CVError

router = APIRouter()


@router.get("/me", response_model=List[ApplicationResponse], summary="Danh sách đơn ứng tuyển của tôi")
async def list_my_applications(user: User = Depends(get_current_candidate)):
    return await application_service.list_candidate_applications(user)


@router.get("/{application_id}", response_model=ApplicationResponse, summary="Chi tiết đơn ứng tuyển")
async def get_my_application(
    application_id: str,
    user: User = Depends(get_current_candidate),
):
    try:
        oid = PydanticObjectId(application_id)
    except Exception:
        raise HTTPException(422, "application_id không hợp lệ")
    try:
        return await application_service.get_candidate_application(user, oid)
    except CVError as exc:
        raise HTTPException(exc.status_code, exc.message)


@router.post("", response_model=ApplicationResponse, status_code=201,
             summary="Nộp hồ sơ ứng tuyển + AI chấm điểm CV-JD (UC-C5)")
async def apply_to_job(
    job_id: str = Form(..., description="_id của tin tuyển dụng"),
    file: Optional[UploadFile] = File(default=None, description="CV PDF; bỏ trống = dùng CV trong hồ sơ"),
    required_skills: Optional[str] = Form(
        default=None,
        description="Mảng JSON tên kỹ năng bắt buộc của Job; nếu bỏ trống sẽ lấy từ tin tuyển dụng",
    ),
    user: User = Depends(get_current_candidate),
):
    try:
        oid = PydanticObjectId(job_id)
    except Exception:
        raise HTTPException(422, "job_id không hợp lệ")

    parsed_required_skills: Optional[List[str]] = None
    if required_skills is not None:
        try:
            payload = json.loads(required_skills)
        except json.JSONDecodeError as exc:
            raise HTTPException(422, "required_skills phải là một JSON array hợp lệ") from exc
        if not isinstance(payload, list) or any(
            not isinstance(skill, str) or not skill.strip() for skill in payload
        ):
            raise HTTPException(422, "required_skills phải là mảng các chuỗi không rỗng")
        parsed_required_skills = [skill.strip() for skill in payload]

    try:
        return await application_service.apply_job(user, oid, file, parsed_required_skills)
    except CVError as e:
        raise HTTPException(e.status_code, e.message)
