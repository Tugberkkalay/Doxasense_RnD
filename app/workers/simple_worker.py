# app/workers/simple_worker.py
"""
Simplified worker - Routes all processing to Runpod GPU
No local model loading - just coordinates with Runpod
"""
import time
from typing import Dict, Any
from datetime import datetime

from app.db.mongo_session import get_mongo_db, DocumentDB
from app.routing.file_router import route_file


def process_document_on_runpod(document_id: str) -> Dict[str, Any]:
    """
    Simple worker - sends everything to Runpod
    No model loading, just file handling and DB operations
    """
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
        if job:
            job.meta['progress'] = percent
            job.meta['message'] = message
            job.save_meta()
        print(f"[SimpleWorker] {percent}% - {message}")
    
    try:
        update_progress(10, "Preparing document...")
        
        # Get document
        doc = doc_db.get_document(document_id)
        if not doc:
            return {"error": f"Document {document_id} not found"}
        
        doc_db.update_document(document_id, {"status": "processing"})
        
        update_progress(20, "Sending to GPU...")
        
        # Send to Runpod for processing
        from app.workers.runpod_worker import process_on_runpod
        result = process_on_runpod(document_id)
        
        update_progress(100, "Complete!")
        
        processing_time = time.time() - start_time
        print(f"[SimpleWorker] Document {document_id} processed in {processing_time:.2f}s")
        
        return result
        
    except Exception as e:
        doc_db.update_document(document_id, {"status": "failed"})
        update_progress(0, f"Failed: {str(e)}")
        print(f"[SimpleWorker] Error: {e}")
        raise e
