from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from app.core.config import settings
from app.models.user import User
from app.models.company import Company
from app.models.skill import SkillsTaxonomy
from app.models.job import JobPosting
from app.models.application import Application
from app.models.notification import Notification
from app.models.chat import Conversation, Message  # Thêm 2 model chat

MONGO_URI = settings.MONGO_URI

async def init_db():
    client = AsyncIOMotorClient(MONGO_URI)
    database = client.get_default_database()
    
    await init_beanie(
        database=database,
        document_models=[
            User,
            Company,
            SkillsTaxonomy,
            JobPosting,
            Application,
            Notification,
            Conversation,
            Message
        ]
    )
    print("Core Service: Kết nối MongoDB và sync indexes thành công (kèm Chat)!")