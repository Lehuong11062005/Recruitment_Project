import os
from dotenv import load_dotenv

load_dotenv()  # đọc file .env trong thư mục core-service


class Settings:
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017/recruitment_db")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


settings = Settings()

if not settings.JWT_SECRET_KEY:
    raise RuntimeError(
        "Thiếu JWT_SECRET_KEY. Hãy tạo file .env trong services/core-service "
        "(xem .env.example) và điền JWT_SECRET_KEY."
    )
