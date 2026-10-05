from fastapi import Request, HTTPException, Depends
from jose import jwt, JWTError

from config import settings

def get_token_from_header(request: Request):
    auth = request.headers.get("Authorization")

    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    return auth.split(" ")[1]


def verify_token(token: str = Depends(get_token_from_header)):
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")