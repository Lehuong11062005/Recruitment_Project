from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.deps import get_current_candidate
from app.models.user import User
from app.schemas.user import CVUploadResponse, ProfileResponse, ProfileUpdate
from app.services import cv_service, profile_service
from app.services.cv_utils import CVError

router = APIRouter()


@router.get("/me/profile", response_model=ProfileResponse, summary="Xem hồ sơ cá nhân (UC-C2)")
async def get_my_profile(user: User = Depends(get_current_candidate)):
    return profile_service.to_profile_response(user)


@router.put("/me/profile", response_model=ProfileResponse,
            summary="Cập nhật hồ sơ cá nhân - chỉ gửi trường cần đổi (UC-C2)")
async def update_my_profile(data: ProfileUpdate, user: User = Depends(get_current_candidate)):
    user = await profile_service.update_profile(user, data)
    return profile_service.to_profile_response(user)


@router.delete("/me/profile", response_model=ProfileResponse,
               summary="Xóa trắng nội dung hồ sơ (UC-C2)")
async def reset_my_profile(user: User = Depends(get_current_candidate)):
    user = await profile_service.reset_profile(user)
    return profile_service.to_profile_response(user)


@router.post("/me/cv", response_model=CVUploadResponse,
             summary="Upload CV PDF, thay CV cũ nếu có; AI gợi ý kỹ năng (UC-C3)")
async def upload_my_cv(file: UploadFile = File(...), user: User = Depends(get_current_candidate)):
    try:
        return await cv_service.upload_cv(user, file)
    except CVError as e:
        raise HTTPException(e.status_code, e.message)
