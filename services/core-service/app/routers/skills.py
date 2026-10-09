import re
from typing import List, Optional

from fastapi import APIRouter, Query

from app.models.skill import SkillsTaxonomy
from app.schemas.user import SkillResponse

router = APIRouter()


@router.get("", response_model=List[SkillResponse],
            summary="Danh sách kỹ năng chuẩn để ứng viên chọn khi cập nhật hồ sơ")
async def list_skills(q: Optional[str] = Query(default=None, description="Lọc theo tên"),
                      limit: int = Query(default=50, ge=1, le=200)):
    query = SkillsTaxonomy.find({"name": {"$regex": re.escape(q), "$options": "i"}}) if q else SkillsTaxonomy.find()
    skills = await query.limit(limit).to_list()
    return [SkillResponse(id=s.id, name=s.name, category=s.category) for s in skills]
