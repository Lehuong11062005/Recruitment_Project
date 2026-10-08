from fastapi import APIRouter, Depends, status

from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.user import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services import auth_service

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
             summary="Đăng ký tài khoản (UC-C1, UC-R1)")
async def register(data: RegisterRequest):
    user = await auth_service.register_user(data)
    return auth_service.to_user_response(user)


@router.post("/login", response_model=TokenResponse, summary="Đăng nhập, trả về JWT (UC-C1, UC-R1)")
async def login(data: LoginRequest):
    return await auth_service.login_user(data)


@router.get("/me", response_model=UserResponse, summary="Thông tin tài khoản đang đăng nhập")
async def me(user: User = Depends(get_current_user)):
    return auth_service.to_user_response(user)
