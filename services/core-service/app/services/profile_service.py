from datetime import datetime
from typing import List

from beanie import PydanticObjectId
from fastapi import HTTPException, status

from app.models.skill import SkillsTaxonomy
from app.models.user import CandidateProfile, User
from app.schemas.user import ProfileResponse, ProfileUpdate


def to_profile_response(user: User) -> ProfileResponse:
    p = user.profile or CandidateProfile()
    return ProfileResponse(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        summary=p.summary,
        location=p.location,
        skills=p.skills,
        experience=p.experience,
        education=p.education,
        cv_url=p.cv_url,
    )


async def _validate_skill_ids(ids: List[PydanticObjectId]) -> List[PydanticObjectId]:
    unique = list(dict.fromkeys(ids))  # bỏ trùng, giữ thứ tự
    if not unique:
        return []
    found = await SkillsTaxonomy.find({"_id": {"$in": unique}}).to_list()
    missing = set(unique) - {s.id for s in found}
    if missing:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Kỹ năng không tồn tại: {', '.join(str(m) for m in missing)}",
        )
    return unique


async def update_profile(user: User, data: ProfileUpdate) -> User:
    changes = data.model_dump(exclude_unset=True)
    if user.profile is None:
        user.profile = CandidateProfile()

    # Trường nằm ở cấp user
    if changes.get("full_name"):
        user.full_name = changes["full_name"].strip()
    if "phone" in changes:
        user.phone = changes["phone"]

    # Trường nằm trong profile
    for field in ("summary", "location"):
        if field in changes:
            setattr(user.profile, field, changes[field])
    if "skills" in changes:
        user.profile.skills = await _validate_skill_ids(data.skills or [])
    if "experience" in changes:
        user.profile.experience = changes["experience"] or []
    if "education" in changes:
        user.profile.education = changes["education"] or []

    user.updated_at = datetime.utcnow()
    await user.save()
    return user


async def reset_profile(user: User) -> User:
    """Xóa trắng nội dung hồ sơ (giữ lại cv_url và tài khoản)."""
    old_cv = user.profile.cv_url if user.profile else None
    user.profile = CandidateProfile(cv_url=old_cv)
    user.updated_at = datetime.utcnow()
    await user.save()
    return user
