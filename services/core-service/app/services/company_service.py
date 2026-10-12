from typing import List
from datetime import datetime
from beanie import PydanticObjectId
from fastapi import HTTPException, status
from app.models.company import Company
from app.schemas.company import CompanyCreateSchema, CompanyUpdateSchema

class CompanyService:
    @staticmethod
    async def create_company(data: CompanyCreateSchema) -> Company:
        existing = await Company.find_one(Company.name == data.name, Company.deleted_at == None)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Tên doanh nghiệp đã tồn tại trên hệ thống."
            )
        
        company = Company(
            **data.model_dump(),
            verification_status="PENDING"
        )
        await company.insert()
        return company

    @staticmethod
    async def get_company_by_id(company_id: str) -> Company:
        company = await Company.find_one(
            Company.id == PydanticObjectId(company_id), 
            Company.deleted_at == None
        )
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Không tìm thấy thông tin doanh nghiệp."
            )
        return company

    @staticmethod
    async def update_company(company_id: str, data: CompanyUpdateSchema) -> Company:
        company = await CompanyService.get_company_by_id(company_id)
        
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(company, key, value)
            
        # Duyệt mềm: Khi cập nhật thông tin, trạng thái quay lại PENDING
        company.verification_status = "PENDING"
        company.updated_at = datetime.utcnow()
        
        await company.save()
        return company

    @staticmethod
    async def soft_delete_company(company_id: str) -> bool:
        company = await CompanyService.get_company_by_id(company_id)
        company.deleted_at = datetime.utcnow()
        await company.save()
        return True

    @staticmethod
    async def get_all_companies(skip: int = 0, limit: int = 20) -> List[Company]:
        return await Company.find(Company.deleted_at == None).skip(skip).limit(limit).to_list()