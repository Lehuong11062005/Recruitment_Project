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
    # AI Service thực tế (port 8002); blank environment values use this default too.
    AI_URL: str = os.getenv("AI_URL") or "http://localhost:8002"
    AI_TIMEOUT_SECONDS: float = float(os.getenv("AI_TIMEOUT_SECONDS", "30"))

    # --- Task 9.3: gửi email thông báo qua SMTP (để trống SMTP_HOST = tắt gửi email, chỉ log) ---
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT") or "587")      # 587 = STARTTLS, 465 = SSL
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM") or os.getenv("SMTP_USER", "")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").strip().lower() in ("1", "true", "yes")
    SMTP_TIMEOUT_SECONDS: float = float(os.getenv("SMTP_TIMEOUT_SECONDS") or "15")
    # Dùng để dựng link trong email (ví dụ http://localhost:5173/candidate/applications/<id>)
    FRONTEND_URL: str = os.getenv("FRONTEND_URL") or "http://localhost:5173"


settings = Settings()

if not settings.JWT_SECRET_KEY:
    raise RuntimeError(
        "Thiếu JWT_SECRET_KEY. Hãy tạo file .env trong services/core-service "
        "(xem .env.example) và điền JWT_SECRET_KEY."
    )
