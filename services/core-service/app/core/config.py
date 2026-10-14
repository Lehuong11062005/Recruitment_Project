import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()  # đọc file .env trong thư mục core-service


class Settings:
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017/recruitment_db")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    # --- UC-C3: upload CV ---
    # Thư mục lưu file (tương đối so với thư mục core-service); đã nằm trong .gitignore
    UPLOAD_DIR: Path = (Path(__file__).resolve().parents[2] / os.getenv("UPLOAD_DIR", "uploads")).resolve()
    CV_MAX_SIZE_MB: int = int(os.getenv("CV_MAX_SIZE_MB", "5"))
    # Địa chỉ AI Service, ví dụ http://localhost:8002. Để trống = bỏ qua bước AI phân tích CV
    AI_URL: str = os.getenv("AI_URL", "")
    AI_TIMEOUT_SECONDS: float = float(os.getenv("AI_TIMEOUT_SECONDS", "30"))


settings = Settings()

if not settings.JWT_SECRET_KEY:
    raise RuntimeError(
        "Thiếu JWT_SECRET_KEY. Hãy tạo file .env trong services/core-service "
        "(xem .env.example) và điền JWT_SECRET_KEY."
    )
