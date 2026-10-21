from datetime import datetime
from typing import List, Optional, Tuple
import httpx
from fastapi import HTTPException, status
from app.models.job import JobPosting
from app.models.skill import SkillsTaxonomy
from app.schemas.job import JobCreateSchema, JobUpdateSchema, JobStatusUpdateSchema
from datetime import timezone

class JobService:
    @staticmethod
    async def generate_job_embedding(title: str, description: str, skills: List[str]) -> Tuple[Optional[List[float]], Optional[str]]:
        """
        Gửi văn bản JD sang AI Service để sinh vector nhúng.
        Nếu AI Service lỗi hoặc sập, trả về (None, None) để không làm gián đoạn thao tác của HR.
        """
        ai_service_url = "http://127.0.0.1:8002/api/v1/ai/embed"
        text_to_embed = f"{title}\n{description}\nSkills: {', '.join(skills)}"
        
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.post(ai_service_url, json={"text": text_to_embed})
                if response.status_code == 200:
                    data = response.json()
                    return data.get("embedding_vector"), data.get("model_name", "all-MiniLM-L6-v2")
        except Exception as e:
            print(f"[AI Service Warning] Lỗi sinh embedding: {e}")
        
        return None, None

    @staticmethod
    async def create_job(job_in: JobCreateSchema, current_user) -> JobPosting:
        # Kiểm tra user.company_id != null (400 nếu chưa có hồ sơ doanh nghiệp)
        if not getattr(current_user, "company_id", None):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vui lòng cập nhật hồ sơ doanh nghiệp trước khi đăng tin"
            )
        
        # Gọi AI Service sinh vector nhúng
        vector, model_name = await JobService.generate_job_embedding(
            job_in.title, job_in.description, [str(s) for s in job_in.required_skills]
        )
        
        # Khởi tạo bản ghi với các giá trị mặc định
        job = JobPosting(
            **job_in.model_dump(),
            company_id=current_user.company_id,
            recruiter_id=current_user.id,
            status="OPEN",
            views_count=0,
            applications_count=0,
            job_embedding_vector=vector,
            embedding_model=model_name or "all-MiniLM-L6-v2"
        )
        await job.insert()
        return job

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
        
        update_data = job_in.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()
        
        await job.update({"$set": update_data})
        
        # Cập nhật lại vector nhúng nếu tiêu đề, mô tả hoặc kỹ năng thay đổi
        if any(k in update_data for k in ["title", "description", "required_skills"]):
            vector, model_name = await JobService.generate_job_embedding(
                job.title, job.description, [str(s) for s in job.required_skills]
            )
            await job.update({"$set": {
                "job_embedding_vector": vector,
                "embedding_model": model_name or "all-MiniLM-L6-v2"
            }})
            
        return job

    @staticmethod
    async def update_status(job_id: str, status_in: JobStatusUpdateSchema, current_user):
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
            embedding_model=model_name or "all-MiniLM-L6-v2",
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

        title = update_data.get("title", job.title)
        description = update_data.get("description", job.description)
        required_skills = update_data.get("required_skills", job.required_skills)
        skill_names = await JobService.get_required_skill_names(required_skills)
        vector, model_name = await JobService.generate_job_embedding(
            title,
            description,
            skill_names,
        )
        update_data.update({
            "job_embedding_vector": vector,
            "embedding_model": model_name or "all-MiniLM-L6-v2",
            "updated_at": datetime.now(timezone.utc),
        })
        await job.update({"$set": update_data})
        updated_job = await JobPosting.get(job_id)
        if not updated_job:
            raise HTTPException(status_code=404, detail="Không tìm thấy tin tuyển dụng")
        return updated_job