from datetime import datetime

from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import CandidateProfile, User
from app.schemas.user import LoginRequest, RegisterRequest, TokenResponse, UserResponse


def to_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role,
        user_type=user.user_type,
        company_id=user.company_id,
        status=user.status,
    )


def get_role_claim(user: User) -> str:
    """Giá trị 'role' ghi trong JWT: ADMIN / CANDIDATE / RECRUITER (Gateway dùng để phân quyền)."""
    return "ADMIN" if user.role == "ADMIN" else (user.user_type or "USER")


async def register_user(data: RegisterRequest) -> User:
    email = data.email.lower()
    if await User.find_one(User.email == email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email đã được đăng ký")

    user = User(
        email=email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        phone=data.phone,
        role="USER",                      # không cho tự đăng ký ADMIN
        user_type=data.user_type,
        # Ứng viên có sẵn hồ sơ rỗng để sửa dần; nhà tuyển dụng thì không có profile
        profile=CandidateProfile() if data.user_type == "CANDIDATE" else None,
    )
    try:
        await user.insert()
    except DuplicateKeyError:             # 2 người đăng ký cùng email cùng lúc
        raise HTTPException(status.HTTP_409_CONFLICT, "Email đã được đăng ký")
    return user


async def login_user(data: LoginRequest) -> TokenResponse:
    user = await User.find_one(User.email == data.email.lower())
    # Cùng một thông báo cho "sai email" và "sai mật khẩu" để không lộ email nào tồn tại
    if (
        user is None
        or user.deleted_at is not None
        or not verify_password(data.password, user.password_hash)
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email hoặc mật khẩu không đúng")
    if user.status != "ACTIVE":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Tài khoản đã bị khóa")

    token = create_access_token(
        {"sub": str(user.id), "email": user.email, "role": get_role_claim(user)}
    )
    return TokenResponse(access_token=token, user=to_user_response(user))
