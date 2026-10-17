from datetime import datetime
from fastapi import HTTPException, status
from app.models.company import Company
from app.models.user import User
from app.schemas.company import CompanyCreateSchema, CompanyUpdateSchema


class CompanyService:
    @staticmethod
    async def create_company(data: CompanyCreateSchema, current_user: User) -> Company:
        # Kiểm tra vai trò Recruiter
        if getattr(current_user, "user_type", None) != "RECRUITER":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chỉ tài khoản RECRUITER mới có quyền tạo hồ sơ công ty."
            )

        # Kiểm tra xem user đã có company_id chưa (nếu != null thì không được tạo mới nữa)
        if getattr(current_user, "company_id", None) is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tài khoản của bạn đã liên kết với một doanh nghiệp."
            )

        # Kiểm tra trùng tên công ty (409 Conflict)
        existing_company = await Company.find_one(Company.name == data.name)
        if existing_company:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Tên doanh nghiệp đã tồn tại"
            )

        now = datetime.utcnow()
        company = Company(
            **data.model_dump(),
            verification_status="PENDING",  
            created_at=now,
            updated_at=now,
            deleted_at=None
        )
        await company.insert()

        # Cập nhật users.company_id = company.id
        current_user.company_id = company.id
        await current_user.save()

        return company

    @staticmethod
    async def get_company_by_id(company_id: str) -> Company:
        company = await Company.get(company_id)
        if not company or getattr(company, "deleted_at", None) is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy thông tin doanh nghiệp."
            )
        return company

    @staticmethod
    async def update_company(company_id: str, data: CompanyUpdateSchema, current_user: User) -> Company:
        company = await CompanyService.get_company_by_id(company_id)

        # Kiểm tra quyền sở hữu: user.company_id == company_id
        if str(getattr(current_user, "company_id", "")) != str(company.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền chỉnh sửa thông tin của doanh nghiệp khác."
            )

        # Nếu đổi tên, kiểm tra trùng tên mới với công ty khác
        update_data = data.model_dump(exclude_unset=True)
        if "name" in update_data and update_data["name"] != company.name:
            conflict = await Company.find_one(Company.name == update_data["name"])
            if conflict:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Tên doanh nghiệp đã tồn tại"
                )

        for key, value in update_data.items():
            setattr(company, key, value)

        # Đặt lại trạng thái PENDING khi cập nhật thông tin
        company.verification_status = "PENDING"
        company.updated_at = datetime.utcnow()
        await company.save()

        return company

    @staticmethod
    async def get_all_companies(skip: int = 0, limit: int = 20):
        return await Company.find(Company.deleted_at == None).skip(skip).limit(limit).to_list()