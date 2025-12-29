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
    Process document on Runpod GPU - sends file, receives results
    """
    print(f"[Runpod] Processing document {document_id} on GPU...")
    
    # Get Runpod config
    runpod_endpoint = os.getenv("RUNPOD_ENDPOINT", "")
    runpod_api_key = os.getenv("RUNPOD_API_KEY", "")
    
    if not runpod_endpoint or not runpod_api_key:
        print(f"[Runpod] Not configured, using local fallback")
        from app.workers.document_processor_mongo import process_document_mongo
        return process_document_mongo(document_id)
    
    # Get document from DB
    from app.db.mongo_session import get_mongo_db, DocumentDB
    db = get_mongo_db()
    doc_db = DocumentDB(db)
    doc = doc_db.get_document(document_id)
    
    if not doc:
        raise Exception(f"Document {document_id} not found")
    
    # Read file
    with open(doc["storage_path"], "rb") as f:
        file_data = f.read()
    
    # Encode file as base64 for API transfer
    import base64
    file_base64 = base64.b64encode(file_data).decode('utf-8')
    
    # Prepare Runpod request
    payload = {
        "input": {
            "document_id": document_id,
            "filename": doc["original_name"],
            "mime_type": doc.get("mime_type", ""),
            "file_data": file_base64,  # Base64 encoded file
        }
    }
    
    headers = {
        "Authorization": f"Bearer {runpod_api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        # Send to Runpod
        print(f"[Runpod] Sending to GPU endpoint...")
        response = requests.post(
            f"{runpod_endpoint}/run",
            json=payload,
            headers=headers,
            timeout=300
        )
        response.raise_for_status()
        
        runpod_result = response.json()
        job_id = runpod_result.get("id")
        
        # Poll for result
        print(f"[Runpod] Job queued: {job_id}, polling for result...")
        max_attempts = 60  # 5 minutes max
        for attempt in range(max_attempts):
            time.sleep(5)
            
            status_response = requests.get(
                f"{runpod_endpoint}/status/{job_id}",
                headers=headers,
                timeout=30
            )
            status_data = status_response.json()
            
            if status_data.get("status") == "COMPLETED":
                output = status_data.get("output", {})
                print(f"[Runpod] Processing completed!")
                
                # Save results to MongoDB
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
                
                # Update document
                doc_db.update_document(document_id, {
                    "status": "processed",
                    "processed_at": datetime.utcnow()
                })
                
                return {
                    "document_id": document_id,
                    "status": "completed",
                    "processing_time": output.get("processing_time", 0),
                    "gpu_used": True
                }
            
            elif status_data.get("status") == "FAILED":
                error = status_data.get("error", "Unknown error")
                raise Exception(f"Runpod processing failed: {error}")
            
            # Still processing...
            print(f"[Runpod] Status: {status_data.get('status')}, attempt {attempt+1}/{max_attempts}")
        
        # Timeout
        raise Exception("Runpod processing timeout")
        
    except Exception as e:
        print(f"[Runpod] Error: {e}, falling back to local")
        # Fallback - but will fail due to disk space
        raise Exception(f"Runpod failed and local processing disabled: {e}")
