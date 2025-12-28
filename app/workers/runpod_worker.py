# app/workers/runpod_worker.py
"""
Runpod Serverless Worker
- Sends processing jobs to Runpod GPU instances
- Handles async communication
"""
import os
import requests
from typing import Dict, Any

RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY", "")
RUNPOD_ENDPOINT = os.getenv("RUNPOD_ENDPOINT", "")

# For now, fallback to local processing if Runpod not configured
USE_RUNPOD = bool(RUNPOD_API_KEY and RUNPOD_ENDPOINT)


def process_on_runpod(document_id: str) -> Dict[str, Any]:
    """
    Process document on Runpod GPU
    
    If Runpod not configured, falls back to local processing
    """
    if not USE_RUNPOD:
        print(f"[Runpod] Not configured, falling back to local processing")
        from app.workers.document_processor_mongo import process_document_mongo
        return process_document_mongo(document_id)
    
    # Get document info from DB
    from app.db.mongo_session import get_mongo_db, DocumentDB
    db = get_mongo_db()
    doc_db = DocumentDB(db)
    doc = doc_db.get_document(document_id)
    
    if not doc:
        raise Exception(f"Document {document_id} not found")
    
    # Prepare payload for Runpod
    payload = {
        "input": {
            "document_id": document_id,
            "file_path": doc["storage_path"],
            "filename": doc["original_name"],
            "mime_type": doc.get("mime_type", ""),
        }
    }
    
    # Send to Runpod
    headers = {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            f"{RUNPOD_ENDPOINT}/run",
            json=payload,
            headers=headers,
            timeout=300  # 5 min timeout
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Update document with results
        if result.get("status") == "COMPLETED":
            output = result.get("output", {})
            
            # Save to MongoDB
            doc_db.create_normalized_doc({
                "document_id": document_id,
                "modality": output.get("modality", "unknown"),
                "source_filename": doc["original_name"],
                "source_mime": doc.get("mime_type", ""),
                "main_text": output.get("text", ""),
                "summary_text": output.get("summary", ""),
                "tags": output.get("tags", []),
                "labels": output.get("labels", []),
                "captions": output.get("captions", []),
                "extra_metadata": output.get("metadata", {}),
                "embedding": output.get("embedding", []),
                "processing_time_seconds": output.get("processing_time", 0)
            })
            
            # Update document status
            from datetime import datetime
            doc_db.update_document(document_id, {
                "status": "processed",
                "processed_at": datetime.utcnow()
            })
            
            return {
                "document_id": document_id,
                "status": "completed",
                "processing_time": output.get("processing_time", 0)
            }
        else:
            raise Exception(f"Runpod processing failed: {result}")
            
    except Exception as e:
        print(f"[Runpod] Error: {e}, falling back to local")
        # Fallback to local processing
        from app.workers.document_processor_mongo import process_document_mongo
        return process_document_mongo(document_id)
