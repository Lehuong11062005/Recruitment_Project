import json
import re
import fitz  # PyMuPDF
from typing import List, Dict, Any
from fastapi import HTTPException

from app.core.config import settings
from app.core.model_loader import ModelLoader
from app.schemas.matching import ParseCVResponse


class CVParserService:
    _taxonomy_cache: List[Dict[str, Any]] = []

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
            pages = [page.get_text("text", sort=True) for page in doc]
            doc.close()
            return re.sub(r"\s+", " ", "\n".join(pages)).strip()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Lỗi đọc file PDF: {str(exc)}")

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
        parsed_text = cls.extract_text_from_pdf(pdf_bytes)
        if not parsed_text:
            raise HTTPException(
                status_code=422,
                detail="Không trích xuất được văn bản từ PDF; CV có thể là bản scan cần OCR.",
            )
        skills = cls.extract_skills(parsed_text)
        model = ModelLoader.get_model()
        embedding = model.encode(parsed_text).tolist()

        return ParseCVResponse(
            status="success",
            filename=filename,
            parsed_text=parsed_text,
            skills=skills,
            extracted_skills=skills,
            embedding_vector=embedding,
        )