# app/api/ingest.py
from pathlib import Path
import os
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from typing import Any, Dict, List

from app.db.mongo_session import get_db, DocumentDB

from extraction.ocr_pipeline import OcrPipeline
from extraction.audio_pipeline import AudioPipeline
from extraction.vision_pipeline import VisionPipeline
from app.summarization.service import SummarizationService
from app.embedding.enhanced_embedding_service import EnhancedEmbeddingService
from app.nlp.tag_extraction_service import TagExtractionService


router = APIRouter(prefix="/api/ingest", tags=["ingest"])

# ----------------- Global singleton'lar (lazy init) ----------------- #
_ocr = None
_audio = None
_vision = None
_summarizer = None
_embedder = None
_tag_extractor = None


def get_ocr() -> OcrPipeline:
    global _ocr
    if _ocr is None:
        _ocr = OcrPipeline(tesseract_lang="tur+eng")
    return _ocr


def get_audio() -> AudioPipeline:
    global _audio
    if _audio is None:
        print("[API] Loading Whisper-large-v3...")
        _audio = AudioPipeline()
    return _audio


def get_vision() -> VisionPipeline:
    global _vision
    if _vision is None:
        print("[API] Loading BLIP-2...")
        _vision = VisionPipeline()
    return _vision


def get_summarizer() -> SummarizationService:
    global _summarizer
    if _summarizer is None:
        print("[API] Loading mT5 summarization...")
        _summarizer = SummarizationService()
    return _summarizer


def get_embedder() -> EnhancedEmbeddingService:
    global _embedder
    if _embedder is None:
        print("[API] Loading BGE-M3 embedding...")
        _embedder = EnhancedEmbeddingService()
    return _embedder


def get_tag_extractor() -> TagExtractionService:
    global _tag_extractor
    if _tag_extractor is None:
        print("[API] Loading KeyBERT...")
        _tag_extractor = TagExtractionService()
    return _tag_extractor


# ----------------- Yükleme klasörü ----------------- #
UPLOAD_ROOT = Path("data/uploads")
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)


def save_upload_file(file: UploadFile) -> str:
    """
    Dosyayı local diske kaydeder, yeni path'i döner.
    """
    ext = os.path.splitext(file.filename)[1]
    file_id = str(uuid.uuid4())
    new_name = f"{file_id}{ext}"
    dest = UPLOAD_ROOT / new_name

    contents = file.file.read()
    with dest.open("wb") as f:
        f.write(contents)

    return str(dest)


# ----------------- Health ----------------- #
@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Sadece API'nın ayakta olduğunu gösterir.
    Burada hiçbir model load ETMİYORUZ.
    """
    return {"status": "ok", "component": "ingest"}


# ----------------- 1) Hızlı PoC: Senkron /auto endpoint'i ----------------- #
@router.post("/auto")
async def ingest_auto(
    file: UploadFile = File(...),
) -> Dict[str, Any]:
    """
    Hızlı test için:
    - Dosyayı memory'e alır
    - Modaliteye göre ilgili pipeline'ı çalıştırır
    - Summary + labels ekler
    - DB'ye kaydetmez, sadece JSON döner
    """
    data = await file.read()
    filename = file.filename.lower()
    content_type = file.content_type or ""

    main_text = ""
    summary_text = ""
    captions: List[str] = []
    modality = "text"

    # Basit router: uzantı üzerinden
    if filename.endswith((".pdf", ".docx", ".txt")):
        extracted = get_ocr().auto_extract(filename, data)
        main_text = extracted.text
        modality = "text"

    elif filename.endswith((".wav", ".mp3", ".m4a", ".ogg")):
        transcript = get_audio().transcribe_audio(data, filename)
        main_text = transcript.text
        modality = "audio"

    elif filename.endswith((".mp4", ".mov", ".mkv", ".avi")):
        transcript = get_audio().transcribe_video(data, filename)
        main_text = transcript.text
        modality = "video"

    elif filename.endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff")):
        img_analysis = get_vision().analyze_image(data, filename)
        main_text = " ".join(
            part
            for part in [
                img_analysis.ocr_text or "",
                " ".join(img_analysis.blip_captions),
            ]
            if part
        ).strip()
        captions = img_analysis.blip_captions
        modality = "image"

    else:
        # fallback → text gibi davran
        extracted = get_ocr().auto_extract(filename, data)
        main_text = extracted.text
        modality = "text"

    if not main_text:
        raise HTTPException(status_code=400, detail="İçerikten metin çıkarılamadı.")

    # Summary
    summary_text = get_summarizer().summarize(main_text)

    # Tags (KeyBERT)
    tags = get_tag_extractor().extract_tags_from_multimodal(
        full_text=main_text,
        summary=summary_text,
        captions=captions,
        top_n=10
    )

    # Embedding
    embedding = get_embedder().embed_for_search(
        full_text=main_text,
        summary=summary_text,
        tags=tags
    )

    return {
        "modality": modality,
        "source_filename": file.filename,
        "source_mime": content_type,
        "main_text_preview": main_text[:500],
        "summary_text": summary_text,
        "captions": captions,
        "tags": tags,
        "embedding_dim": len(embedding),
    }


# ----------------- 2) Non-blocking upload with queue ----------------- #
@router.post("/upload")
async def ingest_upload(
    file: UploadFile = File(...),
    use_gpu: bool = False,  # Optional: force GPU processing
    db = Depends(get_db),
) -> Dict[str, Any]:
    """
    Non-blocking document upload with queue
    - Saves file immediately
    - Queues processing job
    - Returns job_id for status tracking
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Dosya adı boş.")

    storage_path = save_upload_file(file)
    
    # Get file size
    file_size = os.path.getsize(storage_path)

    doc_db = DocumentDB(db)
    doc = doc_db.create_document({
        "original_name": file.filename,
        "mime_type": file.content_type or "application/octet-stream",
        "size_bytes": file_size,
        "storage_backend": "local_fs",
        "storage_path": storage_path,
        "status": "queued",
    })

    # Enqueue processing job
    from app.queue import enqueue_document_processing
    
    job = enqueue_document_processing(
        document_id=doc["_id"],
        use_gpu=use_gpu
    )
    
    # Store job_id in document for reference
    doc_db.update_document(doc["_id"], {"job_id": job.id})
    
    return {
        "document_id": doc["_id"],
        "job_id": job.id,
        "status": "queued",
        "message": "Document queued for processing. Use job_id to check status."
    }


# ----------------- Job Status Endpoint ----------------- #
@router.get("/job/{job_id}/status")
async def get_job_status_endpoint(job_id: str) -> Dict[str, Any]:
    """
    Get processing job status
    
    Returns:
        - status: queued, processing, completed, failed
        - progress: 0-100
        - result: processing result if completed
    """
    from app.queue import get_job_status
    return get_job_status(job_id)


# ----------------- Queue Stats ----------------- #
@router.get("/queue/stats")
async def get_queue_stats_endpoint() -> Dict[str, Any]:
    """
    Get queue statistics
    """
    from app.queue import get_queue_stats
    return get_queue_stats()


# ----------------- 1) List documents ----------------- #
@router.get("/documents")
async def list_documents(
    skip: int = 0,
    limit: int = 50,
    status: str = None,
    db = Depends(get_db),
) -> Dict[str, Any]:
    """
    Tüm dökümanları listeler (pagination ile)
    """
    doc_db = DocumentDB(db)
    documents, total = doc_db.list_documents(skip=skip, limit=limit, status=status)
    
    doc_list = []
    for doc in documents:
        # Get first normalized doc for preview
        normalized_docs = doc_db.get_normalized_docs_by_document(doc["_id"])
        nd = normalized_docs[0] if normalized_docs else None
        
        doc_list.append({
            "id": doc["_id"],
            "original_name": doc.get("original_name", ""),
            "mime_type": doc.get("mime_type", ""),
            "size_bytes": doc.get("size_bytes"),
            "size_mb": round(doc.get("size_bytes", 0) / (1024*1024), 2) if doc.get("size_bytes") else None,
            "status": doc.get("status", "unknown"),
            "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
            "processed_at": doc.get("processed_at").isoformat() if doc.get("processed_at") else None,
            # Preview from normalized_doc
            "modality": nd.get("modality") if nd else "unknown",
            "tags": nd.get("tags", [])[:5] if nd else [],
            "summary_preview": nd.get("summary_text", "")[:200] if nd else "",
        })
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "documents": doc_list
    }


@router.get("/document/{document_id}")
async def get_document(
    document_id: str,
    db = Depends(get_db),
) -> Dict[str, Any]:
    """
    Document + ilgili NormalizedDoc'ları getirir.
    """
    doc_db = DocumentDB(db)
    doc = doc_db.get_document(document_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document bulunamadı.")
    
    normalized_docs = doc_db.get_normalized_docs_by_document(document_id)
    
    normalized_list: List[Dict[str, Any]] = []
    for nd in normalized_docs:
        normalized_list.append({
            "id": nd["_id"],
            "modality": nd.get("modality", ""),
            "source_filename": nd.get("source_filename", ""),
            "source_mime": nd.get("source_mime", ""),
            "language": nd.get("language", ""),
            "created_at": nd.get("created_at").isoformat() if nd.get("created_at") else None,
            "tags": nd.get("tags", []),
            "labels": nd.get("labels", []),
            "captions": nd.get("captions", []),
            "summary_preview": nd.get("summary_text", "")[:500],
            "main_text_preview": nd.get("main_text", "")[:500],
            "extra_metadata": nd.get("extra_metadata", {}),
            "processing_time": nd.get("processing_time_seconds"),
        })

    return {
        "document": {
            "id": doc["_id"],
            "original_name": doc.get("original_name", ""),
            "mime_type": doc.get("mime_type", ""),
            "size_bytes": doc.get("size_bytes"),
            "size_mb": round(doc.get("size_bytes", 0) / (1024*1024), 2) if doc.get("size_bytes") else None,
            "storage_backend": doc.get("storage_backend", "local_fs"),
            "storage_path": doc.get("storage_path", ""),
            "status": doc.get("status", "unknown"),
            "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
            "processed_at": doc.get("processed_at").isoformat() if doc.get("processed_at") else None,
        },
        "normalized_docs": normalized_list,
    }
