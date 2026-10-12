"""Các dependency dùng chung cho router: lấy user hiện tại từ JWT, kiểm tra vai trò."""
from beanie import PydanticObjectId
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import JWTError, decode_access_token
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token không hợp lệ hoặc đã hết hạn",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = PydanticObjectId(payload.get("sub"))
    except (JWTError, Exception):
        raise unauthorized

    user = await User.get(user_id)
    if user is None or user.deleted_at is not None:
        raise unauthorized
    if user.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị khóa")
    return user


async def get_current_candidate(user: User = Depends(get_current_user)) -> User:
    if user.user_type != "CANDIDATE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ ứng viên (CANDIDATE) mới dùng được chức năng này",
        )
    return user
