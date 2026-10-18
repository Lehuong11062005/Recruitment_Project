import re
from typing import List, Optional

from fastapi import APIRouter, Query

from app.models.skill import SkillsTaxonomy
from app.schemas.user import SkillResponse

router = APIRouter()


@router.get("", response_model=List[SkillResponse],
            summary="Danh sách kỹ năng chuẩn (skills_taxonomy) cho bộ chọn tag ở Frontend")
async def list_skills(
    q: Optional[str] = Query(default=None, description="Lọc theo tên (không phân biệt hoa thường)"),
    category: Optional[str] = Query(default=None, description="Lọc theo nhóm: Frontend, Backend, AI..."),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
):
    flt: dict = {}
    if q:
        flt["name"] = {"$regex": re.escape(q), "$options": "i"}
    if category:
        flt["category"] = category
    skills = await SkillsTaxonomy.find(flt).sort("name").skip(skip).limit(limit).to_list()
    return [SkillResponse(id=s.id, name=s.name, category=s.category) for s in skills]


@router.get("/categories", response_model=List[str], summary="Các nhóm kỹ năng để làm tab/bộ lọc")
async def list_categories():
    cats = await SkillsTaxonomy.get_motor_collection().distinct("category")
    return sorted(c for c in cats if c)
