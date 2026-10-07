from fastapi import APIRouter, Request
import httpx

from app.config import settings

router=APIRouter()

@router.api_route("/{path}:{path}",methods=["GET","POST","PUT","DELETE"])
async def proxy_core(path:str,request:Request):
    url=f"{settings.CORE_URL}/{path}"

    async with httpx.AsyncClient as client:
        response=await client.request(
            method=request.method,
            url=url,
            headers=dict(request.headers),
            content=request.body()
        )
    return response.json()