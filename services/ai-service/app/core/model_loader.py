from threading import Lock
from typing import Optional

from sentence_transformers import SentenceTransformer
import torch

from app.core.config import settings


class ModelLoader:
    model: Optional[SentenceTransformer] = None
    _lock = Lock()

    @classmethod
    def load_model(cls) -> SentenceTransformer:
        if cls.model is not None:
            return cls.model
        with cls._lock:
            if cls.model is None:
                print(f"[AI Service] Đang nạp mô hình Sentence-BERT: {settings.MODEL_NAME}...")
                cls.model = SentenceTransformer(settings.MODEL_NAME)
                print("[AI Service] Nạp mô hình thành công!")
            return cls.model

    @classmethod
    def get_model(cls) -> SentenceTransformer:
        return cls.model if cls.model is not None else cls.load_model()

    @classmethod
    def warm_up(cls) -> None:
        with torch.inference_mode():
            cls.get_model().encode(
                ["Ứng viên có kinh nghiệm phát triển phần mềm."],
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )