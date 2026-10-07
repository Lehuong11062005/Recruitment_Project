from fastapi import APIRouter,Request
import httpx
from app.config import settings
router=APIRouter()

@router.api_route("/{path:path}",methods=["GET","PUT","POST","DELETE"],include_in_schema=False)
async def proxy_ai(path:str, request:Request):
    url=f"{settings.AI_URL}/{path}"

    async with httpx.AsyncClient as client:
        response= await client.request(
            method=request.method,
            url=url,
            headers=dict(request.headers),
            content=await request.body()
        )

    return response.json()