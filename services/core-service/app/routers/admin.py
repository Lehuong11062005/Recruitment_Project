from fastapi import APIRouter, Depends

from app.core.deps import get_current_admin
from app.models.user import User
from app.schemas.admin import AdminStatisticsResponse
from app.services import admin_service

router = APIRouter()


@router.get(
    "/statistics",
    response_model=AdminStatisticsResponse,
    summary="Thống kê tổng hợp hệ thống cho Admin (UC-A4 - Task 10.1)",
)
async def get_admin_statistics(
    _current_admin: User = Depends(get_current_admin),
):
    return await admin_service.get_system_statistics()
