from typing import List
from fastapi import APIRouter, status, Query
from app.schemas.company import CompanyCreateSchema, CompanyUpdateSchema, CompanyResponseSchema
from app.services.company_service import CompanyService

router = APIRouter(prefix="/companies", tags=["Company Profile"])

@router.post("", response_model=CompanyResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_company(data: CompanyCreateSchema):
    return await CompanyService.create_company(data)

@router.get("/{company_id}", response_model=CompanyResponseSchema)
async def get_company(company_id: str):
    return await CompanyService.get_company_by_id(company_id)

@router.put("/{company_id}", response_model=CompanyResponseSchema)
async def update_company(company_id: str, data: CompanyUpdateSchema):
    return await CompanyService.update_company(company_id, data)

@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(company_id: str):
    await CompanyService.soft_delete_company(company_id)
    return None

@router.get("", response_model=List[CompanyResponseSchema])
async def list_companies(skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    return await CompanyService.get_all_companies(skip=skip, limit=limit)