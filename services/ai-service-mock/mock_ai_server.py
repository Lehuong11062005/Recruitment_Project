"""AI Service GIẢ để Cường test luồng nộp hồ sơ khi AI thật của Hưởng chưa xong.
Cũng là bản "hợp đồng API" để gửi cho Hưởng làm theo.

Cài:  pip install fastapi uvicorn python-multipart pymupdf
Chạy: uvicorn mock_ai_server:app --port 8002
"""
import json
import re
from typing import List

import fitz  # PyMuPDF
from fastapi import FastAPI, File, Form, UploadFile

app = FastAPI(title="MOCK AI Service")

KNOWN = ["Python", "Java", "C#", "Node.js", "FastAPI", "Django", "SQL", "MongoDB", "Redis", "ReactJS",
         "React", "TypeScript", "JavaScript", "Docker", "Kubernetes", "AWS", "Git", "Machine Learning", "NLP"]


def _pdf_text(data: bytes) -> str:
    with fitz.open(stream=data, filetype="pdf") as doc:
        return "\n".join(page.get_text() for page in doc).strip()


def _has(text: str, skill: str) -> bool:
    return re.search(r"(?<![\w+#.])" + re.escape(skill) + r"(?![\w+#])", text, re.I) is not None


@app.post("/api/v1/ai/parse-cv")                      # UC-C3: gợi ý kỹ năng khi upload CV
async def parse_cv(file: UploadFile = File(...)):
    text = _pdf_text(await file.read())
    return {"skills": [s for s in KNOWN if _has(text, s)]}


@app.post("/api/v1/ai/match-cv")                      # UC-C5: chấm điểm CV - JD khi nộp đơn
async def match_cv(file: UploadFile = File(...), jd_text: str = Form(""), required_skills: str = Form("[]")):
    text = _pdf_text(await file.read())
    required: List[str] = json.loads(required_skills)
    matched = [s for s in required if _has(text, s)]
    missing = [s for s in required if s not in matched]
    score = 100.0 * len(matched) / len(required) if required else 0.0
    return {
        "parsed_text": text,
        "match_score": round(score, 2),               # 0..100
        "matched_skills": matched,                     # tên kỹ năng (khớp name/aliases trong skills_taxonomy)
        "missing_skills": missing,
        "score_breakdown": {"skill_match": round(score, 2)},
        "recommendation": ("Thiếu: " + ", ".join(missing)) if missing else "CV đáp ứng đủ kỹ năng yêu cầu",
        "embedding": None,                             # AI thật: list[float] vector SBERT của CV
        "model_version": "mock-v0",
    }
