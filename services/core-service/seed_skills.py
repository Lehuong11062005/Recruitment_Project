"""Nạp kỹ năng mẫu vào collection skills_taxonomy.

Đặt file này trong services/core-service/ rồi chạy:   python seed_skills.py
Chạy lại nhiều lần vẫn an toàn (kỹ năng đã có thì bỏ qua).
"""
import asyncio

from app.core.database import init_db
from app.models.skill import SkillsTaxonomy

SKILLS = [
    # (name, category, aliases)
    ("ReactJS", "Frontend", ["React", "React.js"]),
    ("JavaScript", "Frontend", ["JS", "ES6"]),
    ("TypeScript", "Frontend", ["TS"]),
    ("HTML/CSS", "Frontend", ["HTML", "CSS"]),
    ("VueJS", "Frontend", ["Vue", "Vue.js"]),
    ("TailwindCSS", "Frontend", ["Tailwind"]),
    ("Python", "Backend", []),
    ("FastAPI", "Backend", []),
    ("Django", "Backend", []),
    ("NodeJS", "Backend", ["Node.js", "Node"]),
    ("Java", "Backend", []),
    ("Spring Boot", "Backend", ["Spring"]),
    ("C#/.NET", "Backend", [".NET", "C#", "ASP.NET"]),
    ("PHP", "Backend", ["Laravel"]),
    ("REST API", "Backend", ["RESTful"]),
    ("MongoDB", "Database", ["Mongo"]),
    ("MySQL", "Database", []),
    ("PostgreSQL", "Database", ["Postgres"]),
    ("Redis", "Database", []),
    ("Docker", "DevOps", []),
    ("Git", "DevOps", ["GitHub"]),
    ("CI/CD", "DevOps", []),
    ("AWS", "DevOps", ["Amazon Web Services"]),
    ("Linux", "DevOps", []),
    ("Machine Learning", "AI", ["ML"]),
    ("NLP", "AI", ["Natural Language Processing", "Xử lý ngôn ngữ tự nhiên"]),
    ("PyTorch", "AI", []),
    ("TensorFlow", "AI", []),
    ("Data Analysis", "AI", ["Phân tích dữ liệu"]),
    ("SQL", "Database", []),
    ("Teamwork", "Soft Skill", ["Làm việc nhóm"]),
    ("Communication", "Soft Skill", ["Giao tiếp"]),
    ("Problem Solving", "Soft Skill", ["Giải quyết vấn đề"]),
    ("English", "Soft Skill", ["Tiếng Anh"]),
]


async def main() -> None:
    await init_db()
    added = 0
    for name, category, aliases in SKILLS:
        if await SkillsTaxonomy.find_one(SkillsTaxonomy.name == name):
            continue
        await SkillsTaxonomy(
            name=name,
            category=category,
            aliases=aliases,
            level=["Basic", "Intermediate", "Advanced"],
        ).insert()
        added += 1
    total = await SkillsTaxonomy.count()
    print(f"Đã thêm {added} kỹ năng mới. Tổng hiện có: {total}.")


if __name__ == "__main__":
    asyncio.run(main())
