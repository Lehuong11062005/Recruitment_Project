import os
from sentence_transformers import SentenceTransformer

MODEL_NAME = os.getenv("MODEL_NAME", "paraphrase-multilingual-MiniLM-L12-v2")

class ModelLoader:
    model: SentenceTransformer = None

    @classmethod
    def load_model(cls):
        if cls.model is None:
            print(f"AI Service: Đang nạp mô hình SentenceTransformer ({MODEL_NAME})...")
            cls.model = SentenceTransformer(MODEL_NAME)
            print("AI Service: Nạp mô hình NLP thành công!")
        return cls.model

    @classmethod
    def get_model(cls) -> SentenceTransformer:
        if cls.model is None:
            return cls.load_model()
        return cls.model