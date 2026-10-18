from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Trỏ từ app/core/config.py ra thư mục gốc ai-service/.env
AI_SERVICE_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_FILE_PATH = AI_SERVICE_ROOT / ".env"


class Settings(BaseSettings):
    APP_NAME: str = "Smart Recruitment - AI Engine Service"
    VERSION: str = "1.0.0"
    PORT: int = 8002

    # Cấu hình mô hình Sentence-BERT
    MODEL_NAME: str = "paraphrase-multilingual-MiniLM-L12-v2"
    MATCHING_VERSION: str = "v1.0-SBERT"

    # Giới hạn file PDF và đường dẫn file 135 kỹ năng của Cường
    MAX_PDF_SIZE_MB: int = 10
    SKILL_TAXONOMY_PATH: Path = Path(__file__).resolve().parent / "skill_taxonomy.json"

    # Trọng số chấm điểm AI Matching
    SKILL_WEIGHT: float = 0.50
    SEMANTIC_WEIGHT: float = 0.35
    EXPERIENCE_WEIGHT: float = 0.15

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()