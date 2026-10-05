import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    CORE_URL: str=os.getenv("CORE_URL")
    AI_URL: str=os.getenv("AI_URL")
    JWT_SECRET_KEY: str=os.getenv("JWT_SECRET_KEY")
    ALGORITHM: str=os.getenv("ALGORITHM")
    
settings=Settings()
