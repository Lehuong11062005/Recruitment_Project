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
