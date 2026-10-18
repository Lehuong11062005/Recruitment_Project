"""Nạp dữ liệu thử: từ điển kỹ năng + 1 tin tuyển dụng để test API nộp hồ sơ.
Chạy (trong thư mục services/core-service, đã kích hoạt venv):
    python -m scripts.seed_dev
Chạy lại nhiều lần vẫn an toàn (không tạo trùng).
"""
import asyncio

from app.core.database import init_db
from app.models.job import JobPosting
from app.models.skill import SkillsTaxonomy
from beanie import PydanticObjectId

# (tên chuẩn, nhóm, [alias])
SKILLS = [
    ("Python", "Backend", ["python3"]), ("Java", "Backend", []), ("C#", "Backend", ["csharp"]),
    ("Node.js", "Backend", ["nodejs", "node"]), ("FastAPI", "Backend", []), ("Django", "Backend", []),
    ("Spring Boot", "Backend", ["spring"]), ("SQL", "Database", ["mysql", "postgresql"]),
    ("MongoDB", "Database", ["mongo"]), ("Redis", "Database", []),
    ("ReactJS", "Frontend", ["react", "react.js"]), ("VueJS", "Frontend", ["vue", "vue.js"]),
    ("TypeScript", "Frontend", ["ts"]), ("JavaScript", "Frontend", ["js"]),
    ("HTML/CSS", "Frontend", ["html", "css"]), ("TailwindCSS", "Frontend", ["tailwind"]),
    ("Docker", "DevOps", []), ("Kubernetes", "DevOps", ["k8s"]), ("AWS", "DevOps", []),
    ("Git", "DevOps", ["github"]), ("Machine Learning", "AI", ["ml", "học máy"]),
    ("NLP", "AI", ["xử lý ngôn ngữ tự nhiên"]), ("PyTorch", "AI", []),
    ("Giao tiếp", "Soft Skill", ["communication"]), ("Làm việc nhóm", "Soft Skill", ["teamwork"]),
]


async def main() -> None:
    await init_db()
    added = 0
    for name, cat, aliases in SKILLS:
        if await SkillsTaxonomy.find_one(SkillsTaxonomy.name == name) is None:
            await SkillsTaxonomy(name=name, category=cat, aliases=aliases,
                                 level=["Basic", "Intermediate", "Advanced"]).insert()
            added += 1
    print(f"Skills: thêm mới {added}, tổng {await SkillsTaxonomy.count()}")

    if await JobPosting.find_one(JobPosting.title == "[TEST] Backend Python Developer") is None:
        need = ["Python", "FastAPI", "MongoDB", "Docker", "Git"]
        ids = [s.id for s in await SkillsTaxonomy.find({"name": {"$in": need}}).to_list()]
        job = JobPosting(
            company_id=PydanticObjectId(), recruiter_id=PydanticObjectId(),   # id giả, đủ để test
            title="[TEST] Backend Python Developer",
            description="Phát triển REST API bằng Python/FastAPI, MongoDB, đóng gói Docker, dùng Git.",
            required_skills=ids, level="JUNIOR", experience_required=1, location="Ho Chi Minh",
            salary={"min": 10000000, "max": 20000000, "currency": "VND"},
        )
        await job.insert()
        print("Đã tạo job test, job_id =", job.id)
    else:
        job = await JobPosting.find_one(JobPosting.title == "[TEST] Backend Python Developer")
        print("Job test đã có, job_id =", job.id)


if __name__ == "__main__":
    asyncio.run(main())
