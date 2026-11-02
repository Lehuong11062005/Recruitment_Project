from datetime import datetime
import math
from typing import Any, Dict, List, Optional, Tuple
import logging
import httpx
from fastapi import HTTPException, status
from app.core.config import settings
from app.models.job import JobPosting
from app.models.skill import SkillsTaxonomy
from app.models.user import User
from app.schemas.job import JobCreateSchema, JobUpdateSchema, JobStatusUpdateSchema
from datetime import timezone

logger = logging.getLogger(__name__)

class JobService:
    @staticmethod
    async def get_recommendations(candidate: User) -> Dict[str, Any]:
        candidate_vector = (
            candidate.profile.candidate_embedding
            if candidate.profile is not None
            else None
        )
        if not candidate_vector:
            return {
                "items": [],
                "message": "Tải CV hoặc cập nhật hồ sơ để nhận gợi ý việc làm phù hợp.",
            }

        valid_candidate_vector = [
            float(value) for value in candidate_vector
            if isinstance(value, (int, float)) and math.isfinite(value)
        ]
        if (
            len(valid_candidate_vector) != len(candidate_vector)
            or not valid_candidate_vector
        ):
            return {
                "items": [],
                "message": "Vector hồ sơ không hợp lệ; vui lòng cập nhật lại CV.",
            }
        candidate_norm = math.sqrt(sum(value * value for value in valid_candidate_vector))
        if candidate_norm == 0:
            return {"items": [], "message": "Vector hồ sơ không hợp lệ; vui lòng cập nhật lại CV."}

        jobs = await JobPosting.find(
            {"status": "OPEN", "deleted_at": None}
        ).to_list()
        candidate_skill_ids = {
            str(skill_id) for skill_id in (candidate.profile.skills if candidate.profile else [])
        }
        scored: List[Tuple[float, JobPosting, List[str]]] = []
        for job in jobs:
            vector = job.job_embedding_vector
            if not isinstance(vector, list) or len(vector) != len(valid_candidate_vector):
                continue
            if any(
                not isinstance(value, (int, float)) or not math.isfinite(value)
                for value in vector
            ):
                continue
            numeric_vector = [float(value) for value in vector]
            job_norm = math.sqrt(sum(value * value for value in numeric_vector))
            if job_norm == 0:
                continue
            cosine = sum(
                left * right
                for left, right in zip(valid_candidate_vector, numeric_vector)
            ) / (candidate_norm * job_norm)
            matching_ids = [
                str(skill_id) for skill_id in job.required_skills
                if str(skill_id) in candidate_skill_ids
            ]
            scored.append((max(0.0, min(1.0, cosine)), job, matching_ids))

        scored.sort(key=lambda result: result[0], reverse=True)
        skill_docs = await SkillsTaxonomy.find_all().to_list()
        skill_names = {str(skill.id): skill.name for skill in skill_docs}
        items: List[Dict[str, Any]] = []
        for cosine, job, matching_ids in scored[:5]:
            items.append({
                "id": str(job.id),
                "title": job.title,
                "description": job.description,
                "company_id": str(job.company_id),
                "required_skills": [str(skill_id) for skill_id in job.required_skills],
                "required_skill_names": [
                    skill_names[str(skill_id)]
                    for skill_id in job.required_skills
                    if str(skill_id) in skill_names
                ],
                "matched_skills": [
                    skill_names[skill_id]
                    for skill_id in matching_ids
                    if skill_id in skill_names
                ],
                "level": job.level,
                "experience_required": job.experience_required,
                "salary": job.salary,
                "location": job.location,
                "match_score": round(cosine * 100.0, 1),
            })
        return {
            "items": items,
            "message": "Gợi ý việc làm phù hợp nhất với hồ sơ của bạn.",
        }

    @staticmethod
    async def generate_job_embedding(title: str, description: str, skills: List[str]) -> Tuple[Optional[List[float]], Optional[str]]:
        """
        Gửi văn bản JD sang AI Service để sinh vector nhúng.
        Nếu AI Service lỗi hoặc sập, trả về (None, None) để không làm gián đoạn thao tác của HR.
        """
        ai_service_url = settings.AI_URL.rstrip("/") + "/api/v1/ai/embed"
        text_to_embed = f"{title}\n{description}\nSkills: {', '.join(skills)}"
        
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.post(ai_service_url, json={"text": text_to_embed})
                response.raise_for_status()
                data = response.json()
                embedding = data.get("embedding")
                model_version = data.get("model_version")
                if (
                    isinstance(embedding, list)
                    and all(
                        isinstance(value, (int, float)) and math.isfinite(value)
                        for value in embedding
                    )
                    and model_version
                ):
                    return embedding, model_version
                logger.warning("AI Service returned an invalid embedding response")
        except (httpx.HTTPError, ValueError) as e:
            logger.warning("AI Service embedding request failed: %s", e)
        
        return None, None

    @staticmethod
    async def create_job(job_in: JobCreateSchema, current_user) -> JobPosting:
        # Kiểm tra user.company_id != null (400 nếu chưa có hồ sơ doanh nghiệp)
        if not getattr(current_user, "company_id", None):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vui lòng cập nhật hồ sơ doanh nghiệp trước khi đăng tin"
            )
        
        await JobService.validate_required_skills(job_in.required_skills)
        return await JobService.create_job_with_embedding(job_in, current_user)

    @staticmethod
    async def update_job(job_id: str, job_in: JobUpdateSchema, current_user) -> JobPosting:
        job = await JobPosting.get(job_id)
        if not job or job.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Không tìm thấy tin tuyển dụng")
        
        # Kiểm tra quyền sở hữu chính chủ (job.recruiter_id == current_user.id -> 403 nếu không khớp)
        if job.recruiter_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền chỉnh sửa tin tuyển dụng này"
            )
        
        if job_in.required_skills is not None:
            await JobService.validate_required_skills(job_in.required_skills)
        return await JobService.update_job_with_embedding(job_id, job_in, current_user)

    @staticmethod
    async def update_status(job_id: str, status_in: JobStatusUpdateSchema, current_user):
        if status_in.status not in {"OPEN", "CLOSED", "HIDDEN"}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Trạng thái tin tuyển dụng phải là OPEN, CLOSED hoặc HIDDEN",
            )
        job = await JobPosting.get(job_id)
        if not job or job.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Không tìm thấy tin tuyển dụng")
        
        # Kiểm tra quyền sở hữu chính chủ
        if job.recruiter_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền thay đổi trạng thái tin tuyển dụng này"
            )
        
        job.status = status_in.status
        job.updated_at = datetime.utcnow()
        await job.save()
        
        return {"message": "Cập nhật trạng thái thành công", "status": job.status}

    @staticmethod
    async def validate_required_skills(required_skills: List):
        if not required_skills:
            return

        matching_skills = await SkillsTaxonomy.find(
            {"_id": {"$in": required_skills}}
        ).to_list()
        matching_ids = {str(skill.id) for skill in matching_skills}
        invalid_ids = [skill_id for skill_id in required_skills if str(skill_id) not in matching_ids]
        if invalid_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Một hoặc nhiều kỹ năng yêu cầu không tồn tại trong danh mục kỹ năng",
            )

    @staticmethod
    async def get_required_skill_names(required_skills: List) -> List[str]:
        if not required_skills:
            return []
        skills = await SkillsTaxonomy.find(
            {"_id": {"$in": required_skills}}
        ).to_list()
        names_by_id = {str(skill.id): skill.name for skill in skills}
        return [names_by_id[str(skill_id)] for skill_id in required_skills if str(skill_id) in names_by_id]

    @staticmethod
    async def create_job_with_embedding(job_in: JobCreateSchema, current_user) -> JobPosting:
        if not getattr(current_user, "company_id", None):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vui lòng cập nhật hồ sơ doanh nghiệp trước khi đăng tin",
            )

        skill_names = await JobService.get_required_skill_names(job_in.required_skills)
        vector, model_name = await JobService.generate_job_embedding(
            job_in.title,
            job_in.description,
            skill_names,
        )
        job = JobPosting(
            **job_in.model_dump(),
            company_id=current_user.company_id,
            recruiter_id=current_user.id,
            status="OPEN",
            views_count=0,
            applications_count=0,
            job_embedding_vector=vector,
            embedding_model=model_name or "paraphrase-multilingual-MiniLM-L12-v2",
        )
        await job.insert()
        return job

    @staticmethod
    async def update_job_with_embedding(job_id: str, job_in: JobUpdateSchema, current_user) -> JobPosting:
        job = await JobPosting.get(job_id)
        if not job or job.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Không tìm thấy tin tuyển dụng")
        if job.recruiter_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền chỉnh sửa tin tuyển dụng này",
            )

        update_data = job_in.model_dump(exclude_unset=True)
        if not update_data:
            return job

        if any(field in update_data for field in ("title", "description", "required_skills")):
            title = update_data.get("title", job.title)
            description = update_data.get("description", job.description)
            required_skills = update_data.get("required_skills", job.required_skills)
            skill_names = await JobService.get_required_skill_names(required_skills)
            vector, model_name = await JobService.generate_job_embedding(
                title,
                description,
                skill_names,
            )
            if vector is not None:
                update_data["job_embedding_vector"] = vector
            if model_name:
                update_data["embedding_model"] = model_name
        update_data["updated_at"] = datetime.now(timezone.utc)
        await job.update({"$set": update_data})
        updated_job = await JobPosting.get(job_id)
        if not updated_job:
            raise HTTPException(status_code=404, detail="Không tìm thấy tin tuyển dụng")
        return updated_job