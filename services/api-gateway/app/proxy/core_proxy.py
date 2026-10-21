from fastapi import APIRouter, Request, Response
import httpx

from app.config import settings

router = APIRouter()


@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    include_in_schema=False,
)
async def proxy_core(path: str, request: Request):
    # Tao URL dich tu CORE_URL va duong dan request.
    url = f"{settings.CORE_URL.rstrip('/')}/{path.lstrip('/')}"

       # Doc request body.
    body = await request.body()

    # Khong chuyen header Host cua Gateway sang Core Service.
    headers = dict(request.headers)
    headers.pop("host", None)

    # Chuyen tiep request, bao gom query params.
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            params=request.query_params,
            content=body,
            timeout=60.0,
        )
    # Tra response ve frontend/client.
    return Response(
        content=response.content,
        status_code=response.status_code,
        media_type=response.headers.get("content-type"),
    )