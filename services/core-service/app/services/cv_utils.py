"""Hàm thuần (không đụng DB, không đụng mạng) phục vụ UC-C3 - dễ kiểm thử riêng."""
import re
import unicodedata
from typing import Any, Dict, Iterable, List, Tuple

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


def _norm(name: str) -> str:
    """NFKC + casefold + gộp khoảng trắng."""
    s = unicodedata.normalize("NFKC", name or "").casefold().strip()
    return re.sub(r"\s+", " ", s)


def _compact(name: str) -> str:
    """Bỏ dấu cách . - _ / để 'React.js' / 'react js' / 'React-JS' đều thành 'reactjs'."""
    return re.sub(r"[\s.\-_/]+", "", _norm(name))


def map_skill_names(
    names: Iterable[str], skills: Iterable[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Đổi tên kỹ năng AI trả về (List[str]) thành bản ghi skills_taxonomy.

    skills: [{"id", "name", "aliases", "category"}].
    Trả về (matched, unmapped):
      - matched: [{"id", "name", "category"}], không trùng, giữ thứ tự xuất hiện.
      - unmapped: tên không tìm thấy trong taxonomy (để ghi log / bổ sung alias).
    Ưu tiên tên chuẩn hơn alias; khớp chính xác trước, khớp "rút gọn" sau.
    """
    skills = list(skills)
    exact: Dict[str, Dict[str, Any]] = {}
    compact: Dict[str, Dict[str, Any]] = {}
    for s in skills:                                  # tên chuẩn trước
        exact.setdefault(_norm(s["name"]), s)
        compact.setdefault(_compact(s["name"]), s)
    for s in skills:                                  # rồi tới alias
        for alias in s.get("aliases") or []:
            exact.setdefault(_norm(alias), s)
            compact.setdefault(_compact(alias), s)

    matched: List[Dict[str, Any]] = []
    unmapped: List[str] = []
    seen = set()
    for raw in names:
        hit = exact.get(_norm(raw)) or compact.get(_compact(raw))
        if hit is None:
            if isinstance(raw, str) and raw.strip():
                unmapped.append(raw.strip())
            continue
        if hit["id"] not in seen:
            seen.add(hit["id"])
            matched.append({"id": hit["id"], "name": hit["name"], "category": hit.get("category")})
    return matched, unmapped


def match_skill_names(names: Iterable[str], skills: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Giữ tên cũ để code đang dùng (cv_service) không bị vỡ."""
    return map_skill_names(names, skills)[0]
