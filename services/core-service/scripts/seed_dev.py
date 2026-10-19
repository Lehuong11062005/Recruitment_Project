"""Nạp dữ liệu phát triển: Admin, Recruiter, Job mẫu và taxonomy kỹ năng.
Chạy (trong thư mục services/core-service, đã kích hoạt venv):
    python -m scripts.seed_dev
Đặt SEED_ADMIN_PASSWORD và SEED_RECRUITER_PASSWORD để thay mật khẩu mặc định.
"""
import asyncio
import os

from app.core.database import init_db
from app.core.security import hash_password
from app.models.company import Company
from app.models.job import JobPosting
from app.models.skill import SkillsTaxonomy
from app.models.user import User
from seed_skills import SKILLS

ADMIN_EMAIL = os.getenv("SEED_ADMIN_EMAIL", "admin@example.test").strip().lower()
RECRUITER_EMAIL = os.getenv("SEED_RECRUITER_EMAIL", "recruiter@example.test").strip().lower()
ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD", "AdminDev123!")
RECRUITER_PASSWORD = os.getenv("SEED_RECRUITER_PASSWORD", "RecruiterDev123!")
COMPANY_NAME = "[DEV] Recruitment Demo"
JOB_TITLE = "[DEV] Backend Python Developer"


async def seed_skills() -> None:
    for name, category, aliases in SKILLS:
        if await SkillsTaxonomy.find_one(SkillsTaxonomy.name == name) is None:
            await SkillsTaxonomy(
                name=name,
                category=category,
                aliases=aliases,
                level=["Basic", "Intermediate", "Advanced"],
            ).insert()


async def seed_user(email: str, full_name: str, password: str, **fields: object) -> User:
    user = await User.find_one(User.email == email)
    if user is None:
        user = User(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            **fields,
        )
        await user.insert()
        return user

    user.full_name = full_name
    for name, value in fields.items():
        setattr(user, name, value)
    await user.save()
    return user


async def main() -> None:
    await init_db()
    await seed_skills()

    company = await Company.find_one(Company.name == COMPANY_NAME)
    if company is None:
        company = await Company(
            name=COMPANY_NAME,
            industry="Software Development",
            address="Ho Chi Minh City",
            verification_status="VERIFIED",
        ).insert()

    await seed_user(
        ADMIN_EMAIL,
        "Development Admin",
        ADMIN_PASSWORD,
        role="ADMIN",
        user_type=None,
        company_id=None,
        profile=None,
    )
    recruiter = await seed_user(
        RECRUITER_EMAIL,
        "Development Recruiter",
        RECRUITER_PASSWORD,
        role="USER",
        user_type="RECRUITER",
        company_id=company.id,
        profile=None,
    )

    job = await JobPosting.find_one(
        JobPosting.title == JOB_TITLE,
        JobPosting.recruiter_id == recruiter.id,
    )
    if job is None:
        need = ["Python", "FastAPI", "MongoDB", "Docker", "Git"]
        skills = await SkillsTaxonomy.find({"name": {"$in": need}}).to_list()
        ids_by_name = {skill.name: skill.id for skill in skills}
        job = JobPosting(
            company_id=company.id,
            recruiter_id=recruiter.id,
            title=JOB_TITLE,
            description="Phát triển REST API bằng Python/FastAPI, MongoDB, đóng gói Docker, dùng Git.",
            required_skills=[ids_by_name[name] for name in need if name in ids_by_name],
            level="JUNIOR",
            experience_required=1,
            location="Ho Chi Minh",
            salary={"min": 10000000, "max": 20000000, "currency": "VND"},
        )
        await job.insert()

    print(f"Dev seed completed. Skills: {await SkillsTaxonomy.count()}")
    print(f"Admin: {ADMIN_EMAIL}; Recruiter: {RECRUITER_EMAIL}")
    print(f"Sample job_id: {job.id}")


if __name__ == "__main__":
    asyncio.run(main())
