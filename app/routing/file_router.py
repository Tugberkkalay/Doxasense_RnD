# app/routing/file_router.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class FileModality(str, Enum):
    TEXT = "text"      # pdf, docx, txt
    IMAGE = "image"    # jpg, png, etc.
    AUDIO = "audio"    # wav, mp3, m4a
    VIDEO = "video"    # mp4, mov, mkv
    UNKNOWN = "unknown"


@dataclass
class RoutedFile:
    modality: FileModality
    filename: str
    content: bytes
    content_type: Optional[str] = None
    reason: Optional[str] = None  # debug için açıklama


def _infer_modality(filename: str, content_type: Optional[str]) -> tuple[FileModality, str]:
    name = (filename or "").lower()
    ct = (content_type or "").lower()

    # 1) Uzantı üzerinden
    if name.endswith((".pdf", ".docx", ".txt")):
        return FileModality.TEXT, "extension:text"

    if name.endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif")):
        return FileModality.IMAGE, "extension:image"

    if name.endswith((".wav", ".mp3", ".m4a", ".ogg", ".flac")):
        return FileModality.AUDIO, "extension:audio"

    if name.endswith((".mp4", ".mov", ".mkv", ".avi", ".webm")):
        return FileModality.VIDEO, "extension:video"

    # 2) Content-Type üzerinden
    if ct.startswith("image/"):
        return FileModality.IMAGE, "content-type:image"

    if ct.startswith("audio/"):
        return FileModality.AUDIO, "content-type:audio"

    if ct.startswith("video/"):
        return FileModality.VIDEO, "content-type:video"

    if ct in {"application/pdf", "application/msword",
              "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
              "text/plain"}:
        return FileModality.TEXT, "content-type:text"

    # fallback
    return FileModality.UNKNOWN, "fallback:unknown"


def route_file(
    filename: str,
    content_type: Optional[str],
    content: bytes,
) -> RoutedFile:
    """
    Dosya meta bilgisinden modaliteyi belirleyip RoutedFile döner.
    Worker bu fonksiyonu kullanıyor.
    """
    modality, reason = _infer_modality(filename, content_type)
    return RoutedFile(
        modality=modality,
        filename=filename,
        content=content,
        content_type=content_type,
        reason=reason,
    )
