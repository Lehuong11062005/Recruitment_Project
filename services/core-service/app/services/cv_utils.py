"""Hàm thuần (không đụng DB, không đụng mạng) phục vụ UC-C3 - dễ kiểm thử riêng."""
from typing import Any, Dict, Iterable, List

PDF_MAGIC = b"%PDF-"


class CVError(Exception):
    """Lỗi nghiệp vụ khi xử lý file CV; router đổi thành HTTPException."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def validate_pdf(filename: str, data: bytes, max_bytes: int) -> None:
    """Kiểm tra phần đuôi file, độ rỗng, dung lượng và 5 byte đầu '%PDF-'."""
    if not (filename or "").lower().endswith(".pdf"):
        raise CVError(400, "Chỉ nhận file CV định dạng PDF")
    if len(data) == 0:
        raise CVError(400, "File rỗng")
    if len(data) > max_bytes:
        raise CVError(413, f"File quá lớn, tối đa {max_bytes // (1024 * 1024)} MB")
    if not data.startswith(PDF_MAGIC):
        raise CVError(400, "File không phải PDF hợp lệ")


def parse_ai_skill_names(payload: Any) -> List[str]:
    """Lấy danh sách tên kỹ năng từ JSON AI Service trả về: {"skills": ["Python", ...]}.

    Chấp nhận phần tử là chuỗi hoặc {"name": "..."}; bỏ qua mọi thứ khác.
    """
    if not isinstance(payload, dict):
        return []
    names: List[str] = []
    for item in payload.get("skills") or []:
        if isinstance(item, str):
            name = item
        elif isinstance(item, dict) and isinstance(item.get("name"), str):
            name = item["name"]
        else:
            continue
        name = name.strip()
        if name:
            names.append(name)
    return names


def match_skill_names(names: Iterable[str], skills: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ghép tên kỹ năng AI đọc được với skills_taxonomy (theo name hoặc aliases, không phân biệt hoa thường).

    skills: [{"id": ..., "name": str, "aliases": [str]}]. Trả về [{"id", "name"}], không trùng.
    """
    lookup: Dict[str, Dict[str, Any]] = {}
    for s in skills:
        lookup.setdefault(s["name"].strip().lower(), s)
    for s in skills:  # tên chuẩn được ưu tiên hơn alias nếu trùng
        for alias in s.get("aliases") or []:
            lookup.setdefault(alias.strip().lower(), s)

    result: List[Dict[str, Any]] = []
    seen = set()
    for name in names:
        s = lookup.get(name.strip().lower())
        if s is not None and s["id"] not in seen:
            seen.add(s["id"])
            result.append({"id": s["id"], "name": s["name"]})
    return result
