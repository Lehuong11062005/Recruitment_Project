from sentence_transformers import SentenceTransformer
from app.core.config import settings


class ModelLoader:
    model: SentenceTransformer = None

    @classmethod
    def load_model(cls) -> SentenceTransformer:
        if cls.model is None:
            print(f"[AI Service] Đang nạp mô hình Sentence-BERT: {settings.MODEL_NAME}...")
            cls.model = SentenceTransformer(settings.MODEL_NAME)
            print("[AI Service] Nạp mô hình thành công!")
        return cls.model

    @classmethod
    def get_model(cls) -> SentenceTransformer:
        if cls.model is None:
            return cls.load_model()
        return cls.model