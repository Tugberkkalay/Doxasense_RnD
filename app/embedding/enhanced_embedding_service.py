# app/embedding/enhanced_embedding_service.py
"""
Enhanced embedding service using BGE-M3
- Multilingual support (100+ languages including Turkish)
- 1024-dim vectors (vs 384-dim in old model)
- Better semantic understanding
- Single embedding space for all modalities
"""
from typing import List, Union
import torch
from sentence_transformers import SentenceTransformer
import numpy as np


class EnhancedEmbeddingService:
    """
    BGE-M3 based embedding service for unified multimodal search.
    All content types (text, image captions, transcripts) → same embedding space
    """

    def __init__(self, model_name: str = "BAAI/bge-m3"):
        self.model_name = model_name
        print(f"[EmbeddingService] Loading {model_name}...")
        self.model = SentenceTransformer(model_name)
        
        # Check device
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[EmbeddingService] Using device: {self.device}")

    def embed(self, text: str) -> List[float]:
        """
        Single text → 1024-dim embedding vector
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return [0.0] * 1024

        vec = self.model.encode(
            text,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,  # Important for cosine similarity
        )
        
        return vec.astype(float).tolist()

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Batch embedding for efficiency
        """
        if not texts:
            return []

        # Filter out empty texts
        valid_texts = [t if t and t.strip() else " " for t in texts]

        vecs = self.model.encode(
            valid_texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        
        return [vec.astype(float).tolist() for vec in vecs]

    def embed_for_search(
        self, 
        full_text: str, 
        summary: str, 
        tags: List[str]
    ) -> List[float]:
        """
        Combine multiple text sources for richer embedding.
        
        Strategy: 
        - Prioritize summary (concise, information-dense)
        - Add key tags for semantic boost
        - Optionally include full_text snippet for context
        """
        # Build combined text
        parts = []
        
        # Add summary (highest priority)
        if summary and summary.strip():
            parts.append(summary.strip())
        
        # Add tags as keywords
        if tags:
            tag_text = ", ".join(tags)
            parts.append(tag_text)
        
        # Add snippet from full text if summary is short
        if full_text and len(summary) < 200:
            snippet = full_text[:500].strip()
            if snippet:
                parts.append(snippet)
        
        # Combine all parts
        combined = " | ".join(parts)
        
        return self.embed(combined)

    def similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Cosine similarity between two vectors
        """
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        # Cosine similarity (vectors are already normalized)
        sim = np.dot(v1, v2)
        return float(sim)
