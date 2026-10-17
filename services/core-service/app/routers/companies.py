from typing import List
from fastapi import APIRouter, status, Depends, Query
from app.schemas.company import CompanyCreateSchema, CompanyUpdateSchema, CompanyResponseSchema
from app.services.company_service import CompanyService
from app.core.deps import get_current_user  
from app.models.user import User

router = APIRouter(tags=["Company Profile"])


@router.post(
    "", 
    response_model=CompanyResponseSchema, 
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": "Chưa đăng nhập hoặc token hết hạn"},
        403: {"description": "Không phải tài khoản RECRUITER"},
        409: {"description": "Tên doanh nghiệp đã tồn tại"}
    }
)
async def create_company(
    data: CompanyCreateSchema, 
    current_user: User = Depends(get_current_user) 
):
    return await CompanyService.create_company(data, current_user)


@router.get("", response_model=List[CompanyResponseSchema])
async def list_companies(skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    return await CompanyService.get_all_companies(skip=skip, limit=limit)


@router.get("/{company_id}", response_model=CompanyResponseSchema)
async def get_company(company_id: str):
    return await CompanyService.get_company_by_id(company_id)


@router.put(
    "/{company_id}", 
    response_model=CompanyResponseSchema,
    responses={
        401: {"description": "Chưa đăng nhập"},
        403: {"description": "Không có quyền sở hữu công ty này"},
        409: {"description": "Tên doanh nghiệp bị trùng"}
    }
)
async def update_company(
    company_id: str, 
    data: CompanyUpdateSchema, 
    current_user: User = Depends(get_current_user)  
):
    return await CompanyService.update_company(company_id, data, current_user)