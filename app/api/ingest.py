# app/api/ingest.py
from pathlib import Path
import os
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Document, NormalizedDoc

from extraction.ocr_pipeline import OcrPipeline
from extraction.audio_pipeline import AudioPipeline
from extraction.vision_pipeline import VisionPipeline
from app.summarization.service import SummarizationService
from app.embedding.enhanced_embedding_service import EnhancedEmbeddingService
from app.nlp.tag_extraction_service import TagExtractionService

from app.queue import task_queue
from app.workers.document_processor import process_document


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

    # LLM Labels
    labels = get_label_service().generate_labels(
        main_text=main_text,
        summary_text=summary_text,
        captions=captions,
    )

    return {
        "modality": modality,
        "source_filename": file.filename,
        "source_mime": content_type,
        "main_text_preview": main_text[:500],
        "summary_text": summary_text,
        "captions": captions,
        "labels": labels,
    }


# ----------------- 2) Production flow: upload + RQ job ----------------- #
@router.post("/upload")
async def ingest_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Production senaryosu:
    - Dosyayı diske kaydeder
    - documents tablosuna insert eder
    - RQ ile process_document(document_id) job'unu queue'ya atar
    - Hemen response döner (background'da işlenecek)
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Dosya adı boş.")

    storage_path = save_upload_file(file)

    doc = Document(
        original_name=file.filename,
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=None,
        storage_backend="local_fs",
        storage_path=storage_path,
        status="uploaded",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # RQ job enqueue
    job = task_queue.enqueue(
        process_document,
        doc.id,
        job_timeout=600,  # 10 dakika
    )
    return {
        "document_id": str(doc.id),
        "job_id": job.id,
        "status": "queued",
    }


# ----------------- 3) Document + NormalizedDoc getirme ----------------- #
@router.get("/document/{document_id}")
async def get_document(
    document_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Document + ilgili NormalizedDoc'ları getirir.
    Search sonuçlarında orijinal dosyayı göstermek için kullanışlı.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document bulunamadı.")

    normalized_list: List[Dict[str, Any]] = []
    for nd in doc.normalized_docs:
        normalized_list.append(
            {
                "id": str(nd.id),
                "modality": nd.modality,
                "source_filename": nd.source_filename,
                "source_mime": nd.source_mime,
                "created_at": nd.created_at.isoformat() if nd.created_at else None,
                "labels": nd.labels,
                "captions": nd.captions,
                "summary_preview": (nd.summary_text or "")[:500],
            }
        )

    return {
        "document": {
            "id": str(doc.id),
            "original_name": doc.original_name,
            "mime_type": doc.mime_type,
            "storage_backend": doc.storage_backend,
            "storage_path": doc.storage_path,
            "status": doc.status,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        },
        "normalized_docs": normalized_list,
    }
