# app/workers/document_processor.py
from __future__ import annotations

from typing import Any, List

from app.db.session import SessionLocal
from app.db.models import Document, NormalizedDoc
from app.routing.file_router import route_file, FileModality

# --- Global singleton'lar (ama importlar fonksiyon içinde yapılacak) --- #
_ocr = None
_audio = None
_vision = None
_summarizer = None
_label_service = None
_embedder = None


def get_ocr():
    """OCR pipeline'ı lazy import + lazy init."""
    global _ocr
    if _ocr is None:
        from extraction.ocr_pipeline import OcrPipeline  # ağır olmayan kısım ama yine de child'da kalsın
        _ocr = OcrPipeline(tesseract_lang="tur+eng")
    return _ocr


def get_audio():
    """Whisper audio/video pipeline'ı lazy import + lazy init."""
    global _audio
    if _audio is None:
        from extraction.audio_pipeline import AudioPipeline  # torchaudio + transformers burada load edilecek
        _audio = AudioPipeline()  # offline whisper
    return _audio


def get_vision():
    """BLIP vb. görsel pipeline'ı lazy import + lazy init."""
    global _vision
    if _vision is None:
        from extraction.vision_pipeline import VisionPipeline  # transformers burada load edilecek
        _vision = VisionPipeline()
    return _vision


def get_summarizer():
    """Text summarization servisi (distilbart vs.) lazy init."""
    global _summarizer
    if _summarizer is None:
        from app.summarization.service import SummarizationService  # transformers burada load edilecek
        _summarizer = SummarizationService()
    return _summarizer


def get_label_service():
    """LLM tabanlı label servisi lazy init."""
    global _label_service
    if _label_service is None:
        from app.llm.label_service import LabelService  # openai / transformers burada load edilecek
        _label_service = LabelService(use_remote_api=True)
    return _label_service


def get_embedder():
    """Sentence-transformer embedding servisi lazy init."""
    global _embedder
    if _embedder is None:
        from app.embedding.service import EmbeddingService  # sentence-transformers burada load edilecek
        _embedder = EmbeddingService()
    return _embedder


def process_document(document_id: str) -> dict[str, Any]:
    """
    RQ job fonksiyonu.
    - DB'den Document kaydını alır
    - Dosyayı diskten okur
    - route_file ile modaliteyi belirler
    - ilgili pipeline'lar ile text çıkarır, özet + label + embedding üretir
    - NormalizedDoc tablosuna yazar
    """
    db = SessionLocal()
    try:
        # 1) Document kaydını al
        doc: Document | None = db.query(Document).filter(Document.id == document_id).first()
        if doc is None:
            # RQ logu için basit return
            return {"error": f"Document {document_id} not found"}

        # 2) Dosyayı diskten oku
        with open(doc.storage_path, "rb") as f:
            data = f.read()

        # 3) Router ile modality belirle
        routed = route_file(
            filename=doc.original_name,
            content_type=doc.mime_type or "application/octet-stream",
            content=data,
        )

        # 4) Modaliteye göre metni çıkar
        captions: List[str] = []
        if routed.modality == FileModality.TEXT:
            extracted = get_ocr().auto_extract(routed.filename, routed.content)
            main_text = extracted.text
        elif routed.modality == FileModality.AUDIO:
            transcript = get_audio().transcribe_audio(routed.content, routed.filename)
            main_text = transcript.text
        elif routed.modality == FileModality.VIDEO:
            transcript = get_audio().transcribe_video(routed.content, routed.filename)
            main_text = transcript.text
        elif routed.modality == FileModality.IMAGE:
            analysis = get_vision().analyze_image(routed.content, routed.filename)
            main_text = (analysis.ocr_text or "") + " " + " ".join(analysis.blip_captions)
            main_text = main_text.strip()
            captions = analysis.blip_captions
        else:
            # UNKNOWN → text gibi davran
            extracted = get_ocr().auto_extract(routed.filename, routed.content)
            main_text = extracted.text

        if not main_text:
            main_text = ""

        # 5) Özet
        summary = get_summarizer().summarize(main_text) if main_text else ""

        # 6) Label (LLM veya heuristik)
        labels = get_label_service().generate_labels(
            main_text=main_text,
            summary_text=summary,
            captions=captions,
        )

        # 7) Embedding
        emb = get_embedder().embed(main_text) if main_text else [0.0] * 384

        # 8) NormalizedDoc kaydı
        ndoc = NormalizedDoc(
            document_id=doc.id,
            modality=routed.modality.value if hasattr(routed.modality, "value") else str(routed.modality),
            source_filename=doc.original_name,
            source_mime=doc.mime_type or "application/octet-stream",
            main_text=main_text,
            summary_text=summary,
            captions=captions,
            labels=labels,
            embedding=emb,
        )
        db.add(ndoc)

        # Document status güncelle
        doc.status = "processed"
        db.add(doc)

        db.commit()
        db.refresh(ndoc)

        return {
            "normalized_doc_id": str(ndoc.id),
            "document_id": str(doc.id),
            "modality": ndoc.modality,
            "labels": labels,
        }

    except Exception as e:
        db.rollback()
        # Hata durumunda document status'ü işaretleyelim
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.status = "error"
                db.add(doc)
                db.commit()
        except Exception:
            pass
        # RQ dashboard'ta görebilmen için mesaja yaz
        raise e
    finally:
        db.close()
