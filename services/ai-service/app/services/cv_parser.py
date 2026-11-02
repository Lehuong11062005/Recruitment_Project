import json
import re
import unicodedata
import fitz  # PyMuPDF
from typing import List, Dict, Any, Tuple
from fastapi import HTTPException

from app.core.config import settings
from app.core.model_loader import ModelLoader
from app.schemas.matching import ParseCVResponse


def clean_text(text: str) -> str:
    """Normalize extracted CV text while retaining useful technical punctuation."""
    normalized = unicodedata.normalize("NFC", text)
    allowed_punctuation = set("+#.-/(),:;@_%&'\"!?")
    cleaned: List[str] = []
    for character in normalized:
        category = unicodedata.category(character)
        if character in "\r\n\t":
            cleaned.append("\n" if character in "\r\n" else " ")
        elif category[0] in {"L", "N", "M"} or character.isspace():
            cleaned.append(character)
        elif character in allowed_punctuation:
            cleaned.append(character)
        else:
            cleaned.append(" ")

    lines = []
    for line in "".join(cleaned).splitlines():
        line = re.sub(r"[^\S\n]+", " ", line).strip()
        if line:
            lines.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


class CVParserService:
    _taxonomy_cache: List[Dict[str, Any]] = []

    @staticmethod
    def clean_text(text: str) -> str:
        return clean_text(text)

    @classmethod
    def get_taxonomy(cls) -> List[Dict[str, Any]]:
        if not cls._taxonomy_cache and settings.SKILL_TAXONOMY_PATH.exists():
            with open(settings.SKILL_TAXONOMY_PATH, "r", encoding="utf-8") as f:
                cls._taxonomy_cache = json.load(f)
        return cls._taxonomy_cache

    @classmethod
    def extract_text_from_pdf(cls, pdf_bytes: bytes) -> str:
        max_bytes = settings.MAX_PDF_SIZE_MB * 1024 * 1024
        if len(pdf_bytes) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File PDF vượt quá dung lượng tối đa ({settings.MAX_PDF_SIZE_MB}MB).",
            )
        if not pdf_bytes.startswith(b"%PDF-"):
            raise HTTPException(status_code=400, detail="File tải lên không đúng định dạng PDF chuẩn (%PDF-).")

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            pages: List[str] = []
            try:
                for page in doc:
                    blocks = cls._page_text_blocks(page)
                    pages.append(cls._order_page_blocks(blocks, page.rect.width))
            finally:
                doc.close()
            return clean_text("\n".join(pages))
        except Exception as exc:
            if isinstance(exc, HTTPException):
                raise
            raise HTTPException(status_code=400, detail=f"Lỗi đọc file PDF: {str(exc)}")

    @staticmethod
    def _page_text_blocks(page: fitz.Page) -> List[Tuple[float, float, float, float, str]]:
        blocks: List[Tuple[float, float, float, float, str]] = []
        table_regions: List[Tuple[float, float, float, float]] = []

        find_tables = getattr(page, "find_tables", None)
        if callable(find_tables):
            try:
                for table in find_tables().tables:
                    x0, y0, x1, y1 = map(float, table.bbox)
                    table_regions.append((x0, y0, x1, y1))
                    rows = table.extract() or []
                    table_text = "\n".join(
                        " | ".join(str(cell or "").strip() for cell in row)
                        for row in rows
                    ).strip()
                    if table_text:
                        blocks.append((x0, y0, x1, y1, table_text))
            except (AttributeError, TypeError, ValueError, RuntimeError):
                # Table detection is an optional PyMuPDF feature; text blocks remain usable.
                pass

        for item in page.get_text("blocks"):
            if len(item) < 7 or int(item[6]) != 0:
                continue
            x0, y0, x1, y1 = map(float, item[:4])
            if any(
                max(0.0, min(x1, tx1) - max(x0, tx0))
                * max(0.0, min(y1, ty1) - max(y0, ty0))
                >= max(1.0, (x1 - x0) * (y1 - y0) * 0.5)
                for tx0, ty0, tx1, ty1 in table_regions
            ):
                continue
            text = str(item[4]).strip()
            if text:
                blocks.append((x0, y0, x1, y1, text))
        return blocks

    @staticmethod
    def _order_page_blocks(
        blocks: List[Tuple[float, float, float, float, str]], page_width: float
    ) -> str:
        if not blocks:
            return ""
        midpoint = page_width / 2
        left = [block for block in blocks if block[0] < midpoint]
        right = [block for block in blocks if block[0] >= midpoint]
        has_two_columns = bool(left and right) and any(
            block[2] < page_width * 0.82 for block in left
        ) and any(block[0] > page_width * 0.18 for block in right)
        if not has_two_columns:
            ordered = sorted(blocks, key=lambda block: (block[1], block[0]))
        else:
            spanning = sorted([
                block for block in blocks
                if block[2] - block[0] >= page_width * 0.62
            ], key=lambda block: (block[1], block[0]))
            column_blocks = [block for block in blocks if block not in spanning]
            ordered = []
            region_top = 0.0

            def append_column_region(region_bottom: float) -> None:
                region = [
                    block for block in column_blocks
                    if block[1] >= region_top and block[1] < region_bottom
                ]
                ordered.extend(sorted(
                    (block for block in region if block[0] < midpoint),
                    key=lambda block: (block[1], block[0]),
                ))
                ordered.extend(sorted(
                    (block for block in region if block[0] >= midpoint),
                    key=lambda block: (block[1], block[0]),
                ))

            for full_width_block in spanning:
                append_column_region(full_width_block[1])
                ordered.append(full_width_block)
                region_top = max(region_top, full_width_block[3])

            append_column_region(float("inf"))
        return "\n".join(block[4] for block in ordered)

    @classmethod
    def extract_skills(cls, text: str) -> List[str]:
        taxonomy = cls.get_taxonomy()
        found_skills: List[str] = []

        for item in taxonomy:
            canonical = item.get("skill", "").strip()
            if not canonical:
                continue
            search_terms = [canonical] + item.get("aliases", [])

            for term in search_terms:
                term = term.strip()
                if not term:
                    continue
                if term in ("C", "R"):
                    pattern = r"(?:(?<=[:,\n•;(\s])|^)" + re.escape(term) + r"(?=[,;\n)\s/]|$)(?!\s*(?:CP|TNHH|Level))"
                    if re.search(pattern, text):
                        found_skills.append(canonical)
                        break
                else:
                    pattern = r"(?<![\w#+])" + re.escape(term) + r"(?![\w#+])"
                    if re.search(pattern, text, re.IGNORECASE):
                        found_skills.append(canonical)
                        break

        return found_skills

    @classmethod
    def parse_pdf_full(cls, filename: str, pdf_bytes: bytes) -> ParseCVResponse:
        parsed_text = clean_text(cls.extract_text_from_pdf(pdf_bytes))
        if not parsed_text:
            raise HTTPException(
                status_code=422,
                detail="Không trích xuất được văn bản từ PDF; CV có thể là bản scan cần OCR.",
            )
        skills = cls.extract_skills(parsed_text)
        model = ModelLoader.get_model()
        import torch

        with torch.inference_mode():
            embedding = model.encode(
                parsed_text,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            ).tolist()

        return ParseCVResponse(
            status="success",
            filename=filename,
            parsed_text=parsed_text,
            skills=skills,
            extracted_skills=skills,
            embedding_vector=embedding,
        )