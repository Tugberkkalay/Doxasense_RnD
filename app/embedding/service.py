# app/embedding/service.py
from __future__ import annotations
from typing import List

from sentence_transformers import SentenceTransformer
import numpy as np


class EmbeddingService:
    """
    NormalizedDoc.main_text için embedding üreten servis.
    Şu an: all-MiniLM-L6-v2 (384 boyutlu vektör)
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def embed(self, text: str) -> List[float]:
        """
        Tek bir text için 384 boyutlu embedding döner (Python list[float]).
        DB'de TEXT/JSON olarak saklayacağız.
        """
        if not text:
            return [0.0] * 384

        vec = self.model.encode(
            text,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        # numpy → plain Python list
        return vec.astype(float).tolist()
