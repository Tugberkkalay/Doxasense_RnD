# app/workers/document_processor.py
from __future__ import annotations

import time
from typing import Any, List, Dict
from datetime import datetime

from app.db.session import SessionLocal
from app.db.models import Document, NormalizedDoc
from app.routing.file_router import route_file, FileModality

# --- Global singleton'lar (ama importlar fonksiyon içinde yapılacak) --- #
_ocr = None
_audio = None
_vision = None
_summarizer = None
_embedder = None
_tag_extractor = None


def get_ocr():
    """OCR pipeline'ı lazy import + lazy init."""
    global _ocr
    if _ocr is None:
        from extraction.ocr_pipeline import OcrPipeline
        _ocr = OcrPipeline(tesseract_lang="tur+eng")
    return _ocr


def get_audio():
    """Whisper audio/video pipeline'ı lazy import + lazy init."""
    global _audio
    if _audio is None:
        from extraction.audio_pipeline import AudioPipeline
        print("[Worker] Loading Whisper-large-v3 (this may take a while)...")
        _audio = AudioPipeline()  # Now using whisper-large-v3
    return _audio


def get_vision():
    """BLIP vb. görsel pipeline'ı lazy import + lazy init."""
    global _vision
    if _vision is None:
        from extraction.vision_pipeline import VisionPipeline
        print("[Worker] Loading BLIP-2 vision model...")
        _vision = VisionPipeline()
    return _vision


def get_summarizer():
    """Text summarization servisi (mT5) lazy init."""
    global _summarizer
    if _summarizer is None:
        from app.summarization.service import SummarizationService
        print("[Worker] Loading mT5 summarization model...")
        _summarizer = SummarizationService()  # Now using mT5
    return _summarizer


def get_embedder():
    """Enhanced embedding servisi (BGE-M3) lazy init."""
    global _embedder
    if _embedder is None:
        from app.embedding.enhanced_embedding_service import EnhancedEmbeddingService
        print("[Worker] Loading BGE-M3 embedding model...")
        _embedder = EnhancedEmbeddingService()  # BGE-M3
    return _embedder


def get_tag_extractor():
    """Tag extraction servisi (KeyBERT) lazy init."""
    global _tag_extractor
    if _tag_extractor is None:
        from app.nlp.tag_extraction_service import TagExtractionService
        print("[Worker] Loading KeyBERT tag extraction...")
        _tag_extractor = TagExtractionService()
    return _tag_extractor


def process_document(document_id: str) -> dict[str, Any]:
    """
    RQ job fonksiyonu.
    - DB'den Document kaydını alır
    - Dosyayı diskten okur
    - route_file ile modaliteyi belirler
    - ilgili pipeline'lar ile text çıkarır, özet + tag + embedding üretir
    - NormalizedDoc tablosuna yazar
    """
    start_time = time.time()
    db = SessionLocal()
    
    try:
        # 1) Document kaydını al
        doc: Document | None = db.query(Document).filter(Document.id == document_id).first()
        if doc is None:
            return {"error": f"Document {document_id} not found"}

        # Update status
        doc.status = "processing"
        db.commit()

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
        main_text = ""
        captions: List[str] = []
        extra_metadata: Dict[str, Any] = {}
        
        if routed.modality == FileModality.TEXT:
            extracted = get_ocr().auto_extract(routed.filename, routed.content)
            main_text = extracted.text
            metadata = {
                "source_type": extracted.source_type,
                "pages": len(extracted.pages) if extracted.pages else None
            }
            
        elif routed.modality == FileModality.AUDIO:
            transcript = get_audio().transcribe_audio(routed.content, routed.filename)
            main_text = transcript.text
            metadata = {
                "duration_seconds": transcript.duration_seconds,
                "language": transcript.language
            }
            
        elif routed.modality == FileModality.VIDEO:
            transcript = get_audio().transcribe_video(routed.content, routed.filename)
            main_text = transcript.text
            
            # TODO: Add frame extraction & captioning here
            # For now, just use audio transcript
            metadata = {
                "duration_seconds": transcript.duration_seconds,
                "language": transcript.language,
                "has_video": True
            }
            
        elif routed.modality == FileModality.IMAGE:
            analysis = get_vision().analyze_image(routed.content, routed.filename)
            
            # Combine OCR + captions
            text_parts = []
            if analysis.ocr_text:
                text_parts.append(analysis.ocr_text)
            if analysis.blip_captions:
                text_parts.extend(analysis.blip_captions)
                captions = analysis.blip_captions
            
            main_text = " | ".join(text_parts) if text_parts else "image without text"
            metadata = {
                "has_text": bool(analysis.ocr_text),
                "caption_count": len(analysis.blip_captions)
            }
        else:
            # UNKNOWN → try text extraction
            extracted = get_ocr().auto_extract(routed.filename, routed.content)
            main_text = extracted.text

        if not main_text:
            main_text = ""

        # 5) Summary
        print(f"[Worker] Generating summary...")
        summary = get_summarizer().summarize(main_text) if main_text else ""

        # 6) Tags (KeyBERT)
        print(f"[Worker] Extracting tags...")
        tags = get_tag_extractor().extract_tags_from_multimodal(
            full_text=main_text,
            summary=summary,
            captions=captions,
            top_n=10
        )

        # 7) Embedding (BGE-M3)
        print(f"[Worker] Generating embedding...")
        embedding = get_embedder().embed_for_search(
            full_text=main_text,
            summary=summary,
            tags=tags
        )

        # 8) NormalizedDoc kaydı
        processing_time = time.time() - start_time
        
        ndoc = NormalizedDoc(
            document_id=doc.id,
            modality=routed.modality.value if hasattr(routed.modality, "value") else str(routed.modality),
            source_filename=doc.original_name,
            source_mime=doc.mime_type or "application/octet-stream",
            main_text=main_text,
            summary_text=summary,
            tags=tags,
            labels=[],  # Can be added later for categorization
            captions=captions,
            metadata=metadata,
            processing_time_seconds=round(processing_time, 2)
        )
        ndoc.set_embedding(embedding)
        
        db.add(ndoc)

        # Document status güncelle
        doc.status = "processed"
        doc.processed_at = datetime.utcnow()
        db.add(doc)

        db.commit()
        db.refresh(ndoc)

        print(f"[Worker] Document {document_id} processed successfully in {processing_time:.2f}s")

        return {
            "normalized_doc_id": str(ndoc.id),
            "document_id": str(doc.id),
            "modality": ndoc.modality,
            "tags": tags,
            "processing_time": processing_time
        }

    except Exception as e:
        db.rollback()
        # Hata durumunda document status'ü işaretleyelim
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.status = "failed"
                db.add(doc)
                db.commit()
        except Exception:
            pass
        # RQ dashboard'ta görebilmen için mesaja yaz
        print(f"[Worker] Error processing document {document_id}: {e}")
        raise e
    finally:
        db.close()
