# app/db/models.py
import uuid
import json
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    BigInteger,
    Text,
    ARRAY,
    Integer,
    Float,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    original_name = Column(String(512), nullable=False)
    mime_type = Column(String(128), nullable=False)
    size_bytes = Column(BigInteger, nullable=True)

    storage_backend = Column(String(32), nullable=False, default="local_fs")
    storage_path = Column(String(1024), nullable=False)  # /data/uploads/...

    checksum = Column(String(64), nullable=True)
    status = Column(String(16), nullable=False, default="uploaded")  # uploaded|processing|processed|failed

    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    normalized_docs = relationship(
        "NormalizedDoc",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class NormalizedDoc(Base):
    __tablename__ = "normalized_docs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    document = relationship("Document", back_populates="normalized_docs")

    # Basic metadata
    modality = Column(String(20), nullable=False)          # text | audio | video | image
    source_filename = Column(String(512), nullable=False)
    source_mime = Column(String(128), nullable=False)
    language = Column(String(10), nullable=True, default="tr")  # ISO language code

    # Content
    main_text = Column(Text, nullable=False, default="")        # Full extracted text/transcript
    summary_text = Column(Text, nullable=False, default="")     # Short summary
    
    # Tags & labels
    tags = Column(ARRAY(String), nullable=False, default=[])    # Auto-extracted keywords
    labels = Column(ARRAY(String), nullable=False, default=[])  # Categories/classifications

    # Multimodal specific
    captions = Column(ARRAY(Text), nullable=False, default=[])  # Image/video captions
    
    # Extra metadata (JSON for flexibility) - renamed to avoid SQLAlchemy reserved word
    extra_metadata = Column(JSON, nullable=True)
    # Examples:
    # - Text: {"page_count": 15, "has_tables": true, "table_count": 3}
    # - Image: {"width": 1920, "height": 1080, "detected_objects": ["car", "person"]}
    # - Audio: {"duration_seconds": 320, "speaker_count": 2}
    # - Video: {"duration_seconds": 450, "frame_count": 120, "fps": 30}

    # Embedding (1024-dim vector stored as JSON array or text)
    # Will migrate to pgvector later
    embedding = Column(Text, nullable=True)

    # Processing info
    created_at = Column(DateTime, default=datetime.utcnow)
    processing_time_seconds = Column(Float, nullable=True)

    def set_embedding(self, vector: list):
        """Helper to store embedding as JSON string"""
        self.embedding = json.dumps(vector)
    
    def get_embedding(self) -> list:
        """Helper to load embedding from JSON string"""
        if self.embedding:
            return json.loads(self.embedding)
        return []

