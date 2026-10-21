from fastapi import APIRouter, Request, Response
import httpx

from app.config import settings

router = APIRouter()

@router.api_route("/api/v1/ai/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"], include_in_schema=False)
async def proxy_ai(path: str, request: Request):
    url = f"{settings.AI_URL.rstrip('/')}/api/v1/ai/{path.lstrip('/')}"
    # 1. BẮT BUỘC: await để lấy dữ liệu bytes thật
    body = await request.body()

    # 2. Loại bỏ header host để tránh lệch cổng khi forward
    headers = dict(request.headers)
    headers.pop("host", None)

    # 3. Chuyển tiếp toàn bộ method, query params và body
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            params=request.query_params,
            content=body,
            timeout=60.0,
        )

    # 4. Trả nguyên status code, content và headers về cho client/frontend
    return Response(
        content=response.content,
        status_code=response.status_code,
        media_type=response.headers.get("content-type"),
    )