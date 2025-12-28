# app/db/models.py
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    BigInteger,
    Text,
    ARRAY,
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
    status = Column(String(16), nullable=False, default="uploaded")  # uploaded|processed|failed

    created_at = Column(DateTime, default=datetime.utcnow)

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

    modality = Column(String(20), nullable=False)          # text | audio | video | image
    source_filename = Column(String(512), nullable=False)
    source_mime = Column(String(128), nullable=False)

    main_text = Column(Text, nullable=False)
    summary_text = Column(Text, nullable=False)

    captions = Column(ARRAY(Text), nullable=False, default=[])
    labels = Column(ARRAY(String), nullable=False, default=[])

    # Şimdilik embedding'i JSON string (ör: "[0.1, -0.3, ...]") olarak tut.
    # Sonra pgvector geldiğinde migration yaparız.
    embedding = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
