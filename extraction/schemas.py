# extraction/schemas.py
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import datetime


class ExtractedText(BaseModel):
    text: str
    language: Optional[str] = "tr"
    source_type: str  # pdf, scanned_pdf, docx, image, txt
    pages: Optional[List[str]] = None   # PDF için sayfa sayfa text


class AudioSegment(BaseModel):
    start: float
    end: float
    text: str
    speaker: Optional[str] = None


class AudioTranscript(BaseModel):
    text: str
    language: str
    segments: List[AudioSegment] = []
    duration_seconds: Optional[float] = None
    source_type: str = "audio"      # audio | video


class ImageAnalysis(BaseModel):
    ocr_text: Optional[str] = None
    clip_top_labels: List[str] = []        # CLIP ile bulunan etiketler
    clip_scores: Dict[str, float] = {}     # etiket → cosine skor
    blip_captions: List[str] = []          # BLIP-2 caption çıktıları


# ----------------- BURADAN SONRA YENİ: NormalizedDoc ----------------- #

class NormalizedDoc(BaseModel):
    """
    MIND → CORE arasında kullanılacak ortak şema.
    Tüm modaliteleri (text, image, audio, video) aynı yapıda tutuyoruz.
    """
    id: UUID = Field(default_factory=uuid4)

    modality: Literal["text", "image", "audio", "video"]
    source_filename: str
    source_mime: str

    # Arama için temel metin
    main_text: str

    # Uzun içerikler için kısa özet
    summary_text: str

    # Multimodal ek bilgiler
    captions: List[str] = []
    labels: List[str] = []

    # Opsiyonel ham içerikler
    ocr_text: Optional[str] = None
    transcript: Optional[str] = None

    # Audio özel alanlar
    audio_language: Optional[str] = None
    audio_duration_seconds: Optional[float] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Gerekirse ileride ekstra alanları buraya atarız
    extra: Dict[str, Any] = {}

    # ---------- Helper constructor'lar ----------

    @classmethod
    def from_image(
        cls,
        filename: str,
        content_type: str,
        analysis: ImageAnalysis,
        summary: Optional[str] = None,
    ) -> "NormalizedDoc":
        """
        ImageAnalysis -> NormalizedDoc
        main_text = OCR + caption birleşimi
        labels = clip_top_labels
        """
        ocr_text = analysis.ocr_text or ""
        captions = analysis.blip_captions or []
        labels = analysis.clip_top_labels or []

        main_text_parts = []
        if ocr_text.strip():
            main_text_parts.append(ocr_text.strip())
        if captions:
            main_text_parts.extend([c.strip() for c in captions if c.strip()])

        main_text = " ".join(main_text_parts).strip() or "image without text"
        summary_text = summary or (captions[0] if captions else main_text[:400])

        return cls(
            modality="image",
            source_filename=filename,
            source_mime=content_type,
            main_text=main_text,
            summary_text=summary_text,
            captions=captions,
            labels=labels,
            ocr_text=ocr_text,
            extra={"clip_scores": analysis.clip_scores},
        )

    @classmethod
    def from_audio(
        cls,
        filename: str,
        content_type: str,
        transcript: AudioTranscript,
        summary: Optional[str] = None,
    ) -> "NormalizedDoc":
        text = (transcript.text or "").strip()
        summary_text = summary or text[:600]

        return cls(
            modality="audio",
            source_filename=filename,
            source_mime=content_type,
            main_text=text,
            summary_text=summary_text,
            transcript=text,
            audio_language=transcript.language,
            audio_duration_seconds=transcript.duration_seconds,
        )

    @classmethod
    def from_text(
        cls,
        filename: str,
        content_type: str,
        extracted: ExtractedText,
        summary: Optional[str] = None,
    ) -> "NormalizedDoc":
        text = (extracted.text or "").strip()
        summary_text = summary or text[:600]

        return cls(
            modality="text",
            source_filename=filename,
            source_mime=content_type,
            main_text=text,
            summary_text=summary_text,
            extra={"pages": extracted.pages, "source_type": extracted.source_type},
        )
