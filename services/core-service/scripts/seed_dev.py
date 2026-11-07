"""Idempotently seed demo accounts, companies, jobs, and the AI skill taxonomy.

Run from services/core-service with its environment configured:
    python -m scripts.seed_dev
    python -m scripts.seed_dev --with-ranking  # add synthetic applications and PDFs
"""
import argparse
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from pymongo.errors import DuplicateKeyError

from app.core.database import init_db
from app.core.security import hash_password
from app.core.storage import CV_DIR, UPLOAD_URL_PREFIX
from app.models.application import AIAnalysis, Application, StatusHistory
from app.models.company import Company
from app.models.job import JobPosting
from app.models.skill import SkillsTaxonomy
from app.models.user import CandidateProfile, User
from app.services.profile_pdf import render_profile_pdf
from app.services.profile_service import to_profile_response

ADMIN_EMAIL = os.getenv("SEED_ADMIN_EMAIL", "admin@example.com").strip().lower()
RECRUITER_EMAIL = os.getenv("SEED_RECRUITER_EMAIL", "recruiter@example.com").strip().lower()
RECRUITER_TWO_EMAIL = os.getenv("SEED_RECRUITER_TWO_EMAIL", "recruiter2@example.com").strip().lower()
CANDIDATE_EMAIL = os.getenv("SEED_CANDIDATE_EMAIL", "candidate@example.com").strip().lower()
ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD", "AdminDev123!")
RECRUITER_PASSWORD = os.getenv("SEED_RECRUITER_PASSWORD", "RecruiterDev123!")
CANDIDATE_PASSWORD = os.getenv("SEED_CANDIDATE_PASSWORD", "CandidateDev123!")
TAXONOMY_PATH = (
    Path(__file__).resolve().parents[2]
    / "ai-service"
    / "app"
    / "core"
    / "skill_taxonomy.json"
)

COMPANIES = (
    {
        "name": "[DEV] Recruitment Demo",
        "industry": "Software Development",
        "address": "Ho Chi Minh City",
        "description": "Doanh nghiệp công nghệ mẫu phục vụ demo tuyển dụng.",
    },
    {
        "name": "[DEV] Data Solutions",
        "industry": "Data & AI",
        "address": "Ha Noi",
        "description": "Doanh nghiệp dữ liệu và AI mẫu phục vụ demo tuyển dụng.",
    },
)

SAMPLE_JOBS = (
    ("Backend Python Developer", 0, "Backend", ["Python", "FastAPI", "MongoDB", "Docker", "Git"], "MID", 1, 15000000, 25000000, "Ho Chi Minh City"),
    ("Frontend React Developer", 0, "Frontend", ["JavaScript", "React", "HTML", "CSS", "Git"], "JUNIOR", 0, 12000000, 20000000, "Ho Chi Minh City"),
    ("Full Stack Engineer", 0, "Full stack", ["Python", "React", "REST API", "MongoDB", "Docker"], "MID", 2, 20000000, 35000000, "Remote"),
    ("Machine Learning Engineer", 1, "AI", ["Python", "Machine Learning", "PyTorch", "NLP", "SQL"], "SENIOR", 3, 25000000, 45000000, "Ha Noi"),
    ("Data Analyst", 1, "Analytics", ["Python", "SQL", "Pandas", "Power BI", "Excel"], "JUNIOR", 1, 12000000, 22000000, "Ha Noi"),
    ("DevOps Engineer", 1, "Infrastructure", ["Linux", "Docker", "GitLab CI/CD", "AWS", "Git"], "MID", 2, 20000000, 35000000, "Remote"),
)

RANKING_SCORES = (74, 92, 45, 85, 61, 96, 53, 68, 80)


def load_taxonomy() -> list[dict[str, Any]]:
    with TAXONOMY_PATH.open("r", encoding="utf-8") as file:
        items = json.load(file)
    if not isinstance(items, list) or len(items) != 135:
        raise ValueError(f"Expected 135 skills in {TAXONOMY_PATH}, got {len(items) if isinstance(items, list) else 'invalid data'}")
    if any(not isinstance(item, dict) or not item.get("skill") for item in items):
        raise ValueError(f"Invalid skill entry in {TAXONOMY_PATH}")
    return items


async def seed_skills(items: list[dict[str, Any]]) -> dict[str, Any]:
    result = {}
    for item in items:
        name = item["skill"].strip()
        category = item.get("group")
        aliases = [alias.strip() for alias in item.get("aliases", []) if isinstance(alias, str) and alias.strip()]
        skill = await SkillsTaxonomy.find_one(SkillsTaxonomy.name == name)
        if skill is None:
            skill = SkillsTaxonomy(
                name=name,
                category=category,
                aliases=aliases,
                level=["Basic", "Intermediate", "Advanced"],
            )
        else:
            skill.category = category
            skill.aliases = aliases
            skill.level = ["Basic", "Intermediate", "Advanced"]
        if skill.id:
            await skill.save()
        else:
            await skill.insert()
        result[name] = skill
    return result


async def seed_company(data: dict[str, str]) -> Company:
    company = await Company.find_one(Company.name == data["name"])
    if company is None:
        company = Company(name=data["name"])
    for key, value in data.items():
        setattr(company, key, value)
    company.verification_status = "VERIFIED"
    if company.id:
        await company.save()
    else:
        await company.insert()
    return company


async def seed_user(
    email: str,
    full_name: str,
    password: str,
    **fields: Any,
) -> User:
    user = await User.find_one(User.email == email)
    password_hash = hash_password(password)
    if user is None:
        user = User(email=email, full_name=full_name, password_hash=password_hash)
    user.full_name = full_name
    user.password_hash = password_hash
    for name, value in fields.items():
        setattr(user, name, value)
    if user.id:
        await user.save()
    else:
        await user.insert()
    return user


async def seed_job(
    title: str,
    company: Company,
    recruiter: User,
    area: str,
    required_names: list[str],
    skills_by_name: dict[str, Any],
    level: str,
    experience: int,
    salary_min: int,
    salary_max: int,
    location: str,
) -> JobPosting:
    job = await JobPosting.find_one(
        JobPosting.title == f"[DEV] {title}",
        JobPosting.recruiter_id == recruiter.id,
    )
    if job is None:
        job = JobPosting(
            title=f"[DEV] {title}",
            company_id=company.id,
            recruiter_id=recruiter.id,
            description=(
                f"Tuyển dụng vị trí {title} thuộc nhóm {area}. "
                f"Tham gia phát triển sản phẩm, phối hợp cùng đội ngũ và "
                f"đáp ứng các kỹ năng: {', '.join(required_names)}."
            ),
        )
    job.company_id = company.id
    job.recruiter_id = recruiter.id
    job.required_skills = [skills_by_name[name].id for name in required_names]
    job.level = level
    job.experience_required = experience
    job.salary = {"min": salary_min, "max": salary_max, "currency": "VND"}
    job.location = location
    job.status = "OPEN"
    job.deleted_at = None
    if job.id:
        await job.save()
    else:
        await job.insert()
    return job


def write_sample_pdf(path: Path, candidate: User, skill_names: list[str]) -> None:
    data = render_profile_pdf(to_profile_response(candidate), skill_names)
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, delete=False) as file:
        temporary_path = Path(file.name)
        try:
            file.write(data)
            file.close()
            temporary_path.replace(path)
        finally:
            temporary_path.unlink(missing_ok=True)


async def seed_ranked_applications(jobs: list[JobPosting], taxonomy: dict[str, Any]) -> None:
    names_by_id = {skill.id: skill.name for skill in taxonomy.values()}
    for job_number, job in enumerate(jobs, start=1):
        for number, score in enumerate(RANKING_SCORES, start=1):
            matched_count = round(len(job.required_skills) * score / 100)
            matched = job.required_skills[:matched_count]
            missing = job.required_skills[matched_count:]
            name = f"Ứng viên mẫu {job_number:02d}-{number:02d}"
            summary = f"Hồ sơ thử nghiệm xếp hạng cho vị trí {job.title}."
            candidate = await seed_user(
                f"ranking-{job_number:02d}-{number:02d}@example.com",
                name,
                CANDIDATE_PASSWORD,
                role="USER",
                user_type="CANDIDATE",
                company_id=None,
                profile=CandidateProfile(summary=summary, skills=matched),
            )
            filename = f"seed-ranking-{job.id}.pdf"
            path = CV_DIR / str(candidate.id) / filename
            url = f"{UPLOAD_URL_PREFIX}/cvs/{candidate.id}/{filename}"
            existing = await Application.find_one(
                Application.job_id == job.id, Application.candidate_id == candidate.id,
            )
            if existing is not None and existing.cv_url != url:
                continue
            if not path.exists():
                await asyncio.to_thread(write_sample_pdf, path, candidate, [names_by_id[key] for key in matched])
            if existing is not None:
                continue

            application = Application(
                job_id=job.id,
                candidate_id=candidate.id,
                cv_url=url,
                parsed_text=f"{name}\n{summary}\n{', '.join(names_by_id[key] for key in matched)}",
                pipeline_status="APPLIED",
                status_history=[StatusHistory(status="APPLIED", changed_by=candidate.id)],
                ai_match_score=score,
                matching_version="seed-ranking-v1",
                ai_status="DONE",
                ai_analyzed_at=datetime.now(timezone.utc),
                ai_analysis=AIAnalysis(
                    matched=matched,
                    missing=missing,
                    recommendation="Điểm giả lập dùng để kiểm thử bảng xếp hạng.",
                ),
            )
            try:
                await application.insert()
            except DuplicateKeyError:
                # Another seed process inserted this candidate/job pair.
                pass

        count = await Application.find(Application.job_id == job.id).count()
        await job.update({"$set": {"applications_count": count}})
        print(f"Ranking demo: {job.title} ({job.id}) — {count} applications")


async def main(with_ranking: bool = False) -> None:
    await init_db()
    taxonomy = await seed_skills(load_taxonomy())
    companies = [await seed_company(data) for data in COMPANIES]
    admin = await seed_user(
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
        company_id=companies[0].id,
        profile=None,
    )
    recruiter_two = await seed_user(
        RECRUITER_TWO_EMAIL,
        "Development Recruiter Two",
        RECRUITER_PASSWORD,
        role="USER",
        user_type="RECRUITER",
        company_id=companies[1].id,
        profile=None,
    )
    await seed_user(
        CANDIDATE_EMAIL,
        "Development Candidate",
        CANDIDATE_PASSWORD,
        role="USER",
        user_type="CANDIDATE",
        company_id=None,
        profile=None,
    )

    jobs = []
    for title, company_index, area, skill_names, level, experience, salary_min, salary_max, location in SAMPLE_JOBS:
        unknown = [name for name in skill_names if name not in taxonomy]
        if unknown:
            raise ValueError(f"Sample job {title} references unknown skills: {', '.join(unknown)}")
        selected_recruiter = recruiter if company_index == 0 else recruiter_two
        jobs.append(
            await seed_job(
                title,
                companies[company_index],
                selected_recruiter,
                area,
                skill_names,
                taxonomy,
                level,
                experience,
                salary_min,
                salary_max,
                location,
            )
        )

    print(
        f"Dev seed complete: {await SkillsTaxonomy.count()} skills, "
        f"{len(companies)} companies, {len(jobs)} jobs."
    )
    print(f"Admin: {admin.email}; Recruiters: {recruiter.email}, {recruiter_two.email}; Candidate: {CANDIDATE_EMAIL}")
    print(f"Sample job IDs: {', '.join(str(job.id) for job in jobs)}")
    if with_ranking:
        await seed_ranked_applications(jobs[:2], taxonomy)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed local development data.")
    parser.add_argument("--with-ranking", action="store_true", help="Add 18 sample applications and PDFs.")
    asyncio.run(main(with_ranking=parser.parse_args().with_ranking))
