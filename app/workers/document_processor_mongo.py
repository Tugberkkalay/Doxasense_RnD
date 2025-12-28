# app/workers/document_processor_mongo.py
from __future__ import annotations

import time
from typing import Any, List, Dict
from datetime import datetime

from app.db.mongo_session import get_mongo_db, DocumentDB
from app.routing.file_router import route_file, FileModality

# Global singletons (lazy init)
_ocr = None
_audio = None
_vision = None
_summarizer = None
_embedder = None
_tag_extractor = None


def get_ocr():
    global _ocr
    if _ocr is None:
        from extraction.ocr_pipeline import OcrPipeline
        _ocr = OcrPipeline(tesseract_lang="tur+eng")
    return _ocr


def get_audio():
    global _audio
    if _audio is None:
        from extraction.audio_pipeline import AudioPipeline
        print("[Worker] Loading Whisper-large-v3 (this may take a while)...")
        _audio = AudioPipeline()
    return _audio


def get_vision():
    global _vision
    if _vision is None:
        from extraction.vision_pipeline import VisionPipeline
        print("[Worker] Loading BLIP-2 vision model...")
        _vision = VisionPipeline()
    return _vision


def get_summarizer():
    global _summarizer
    if _summarizer is None:
        from app.summarization.service import SummarizationService
        print("[Worker] Loading mT5 summarization model...")
        _summarizer = SummarizationService()
    return _summarizer


def get_embedder():
    global _embedder
    if _embedder is None:
        from app.embedding.enhanced_embedding_service import EnhancedEmbeddingService
        print("[Worker] Loading BGE-M3 embedding model...")
        _embedder = EnhancedEmbeddingService()
    return _embedder


def get_tag_extractor():
    global _tag_extractor
    if _tag_extractor is None:
        from app.nlp.tag_extraction_service import TagExtractionService
        print("[Worker] Loading KeyBERT tag extraction...")
        _tag_extractor = TagExtractionService()
    return _tag_extractor


def process_document_mongo(document_id: str) -> dict[str, Any]:
    """Process document with MongoDB"""
    start_time = time.time()
    db = get_mongo_db()
    doc_db = DocumentDB(db)
    
    # Get current job for progress updates
    try:
        from rq import get_current_job
        job = get_current_job()
    except:
        job = None
    
    def update_progress(percent: int, message: str = ""):
        """Update job progress"""
        if job:
            job.meta['progress'] = percent
            job.meta['message'] = message
            job.save_meta()
        print(f"[Worker] Progress: {percent}% - {message}")
    
    try:
        update_progress(5, "Loading document...")
        
        # 1) Get document
        doc = doc_db.get_document(document_id)
        if doc is None:
            return {"error": f"Document {document_id} not found"}

        # Update status
        doc_db.update_document(document_id, {"status": "processing"})
        
        update_progress(10, "Reading file...")

        # 2) Read file from disk
        with open(doc["storage_path"], "rb") as f:
            data = f.read()

        update_progress(15, "Detecting file type...")

        # 3) Route by modality
        routed = route_file(
            filename=doc["original_name"],
            content_type=doc.get("mime_type", "application/octet-stream"),
            content=data,
        )

        update_progress(20, f"Processing {routed.modality.value} content...")

        # 4) Extract content
        main_text = ""
        captions: List[str] = []
        extra_metadata: Dict[str, Any] = {}
        
        if routed.modality == FileModality.TEXT:
            update_progress(25, "Extracting text with OCR...")
            extracted = get_ocr().auto_extract(routed.filename, routed.content)
            main_text = extracted.text
            extra_metadata = {
                "source_type": extracted.source_type,
                "pages": len(extracted.pages) if extracted.pages else None
            }
            update_progress(40, "Text extraction complete")
            
        elif routed.modality == FileModality.AUDIO:
            update_progress(25, "Transcribing audio...")
            transcript = get_audio().transcribe_audio(routed.content, routed.filename)
            main_text = transcript.text
            extra_metadata = {
                "duration_seconds": transcript.duration_seconds,
                "language": transcript.language
            }
            update_progress(40, "Audio transcription complete")
            
        elif routed.modality == FileModality.VIDEO:
            update_progress(25, "Extracting audio from video...")
            transcript = get_audio().transcribe_video(routed.content, routed.filename)
            main_text = transcript.text
            extra_metadata = {
                "duration_seconds": transcript.duration_seconds,
                "language": transcript.language,
                "has_video": True
            }
            update_progress(40, "Video transcription complete")
            
        elif routed.modality == FileModality.IMAGE:
            update_progress(25, "Analyzing image...")
            analysis = get_vision().analyze_image(routed.content, routed.filename)
            text_parts = []
            if analysis.ocr_text:
                text_parts.append(analysis.ocr_text)
            if analysis.blip_captions:
                text_parts.extend(analysis.blip_captions)
                captions = analysis.blip_captions
            
            main_text = " | ".join(text_parts) if text_parts else "image without text"
            extra_metadata = {
                "has_text": bool(analysis.ocr_text),
                "caption_count": len(analysis.blip_captions)
            }
            update_progress(40, "Image analysis complete")
        else:
            extracted = get_ocr().auto_extract(routed.filename, routed.content)
            main_text = extracted.text

        if not main_text:
            main_text = ""

        # 5) Summary
        update_progress(50, "Generating summary...")
        summary = get_summarizer().summarize(main_text) if main_text else ""
        update_progress(60, "Summary complete")

        # 6) Tags
        update_progress(65, "Extracting tags...")
        tags = get_tag_extractor().extract_tags_from_multimodal(
            full_text=main_text,
            summary=summary,
            captions=captions,
            top_n=10
        )
        update_progress(75, "Tags extracted")

        # 7) Embedding
        update_progress(80, "Generating embeddings...")
        embedding = get_embedder().embed_for_search(
            full_text=main_text,
            summary=summary,
            tags=tags
        )
        update_progress(90, "Embeddings generated")

        # 8) Create NormalizedDoc
        processing_time = time.time() - start_time
        
        ndoc = doc_db.create_normalized_doc({
            "document_id": document_id,
            "modality": routed.modality.value if hasattr(routed.modality, "value") else str(routed.modality),
            "source_filename": doc["original_name"],
            "source_mime": doc.get("mime_type", "application/octet-stream"),
            "main_text": main_text,
            "summary_text": summary,
            "tags": tags,
            "labels": [],
            "captions": captions,
            "extra_metadata": extra_metadata,
            "embedding": embedding,
            "processing_time_seconds": round(processing_time, 2)
        })

        # Update document status
        doc_db.update_document(document_id, {
            "status": "processed",
            "processed_at": datetime.utcnow()
        })

        update_progress(100, "Processing complete!")

        print(f"[Worker] Document {document_id} processed successfully in {processing_time:.2f}s")

        return {
            "normalized_doc_id": ndoc["_id"],
            "document_id": document_id,
            "modality": ndoc["modality"],
            "tags": tags,
            "processing_time": processing_time
        }

    except Exception as e:
        # Update status to failed
        doc_db.update_document(document_id, {"status": "failed"})
        update_progress(0, f"Failed: {str(e)}")
        print(f"[Worker] Error processing document {document_id}: {e}")
        raise e
