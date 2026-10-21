import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    CORE_URL: str = os.getenv("CORE_URL") or "http://localhost:8001"
    AI_URL: str = os.getenv("AI_URL") or "http://localhost:8002"
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    
settings=Settings()