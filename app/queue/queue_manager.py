# app/queue/queue_manager.py
"""
Queue Manager for document processing
- RQ (Redis Queue) for job management
- Supports multiple concurrent jobs
- Runpod Serverless integration ready
"""
import os
from redis import Redis
from rq import Queue
from rq.job import Job

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_NAME = "doxasense_processing"

# Initialize Redis connection
redis_conn = Redis.from_url(REDIS_URL)

# Create queue
processing_queue = Queue(QUEUE_NAME, connection=redis_conn)


def enqueue_document_processing(document_id: str, use_gpu: bool = False) -> Job:
    """
    Enqueue a document for processing
    
    Args:
        document_id: MongoDB document ID
        use_gpu: If True, route to Runpod GPU worker
    
    Returns:
        RQ Job object
    """
    # Choose worker function based on GPU availability
    if use_gpu:
        from app.workers.runpod_worker import process_on_runpod
        worker_func = process_on_runpod
        timeout = 300  # 5 minutes for GPU
    else:
        from app.workers.document_processor_mongo import process_document_mongo
        worker_func = process_document_mongo
        timeout = 1800  # 30 minutes for CPU
    
    # Enqueue job
    job = processing_queue.enqueue(
        worker_func,
        document_id,
        job_timeout=timeout,
        result_ttl=3600,  # Keep result for 1 hour
        failure_ttl=86400,  # Keep failed jobs for 24 hours
    )
    
    return job


def get_job_status(job_id: str) -> dict:
    """
    Get job status and progress
    
    Returns:
        {
            "id": "job_id",
            "status": "queued|started|finished|failed",
            "progress": 0-100,
            "result": {...} if finished,
            "error": "..." if failed
        }
    """
    try:
        job = Job.fetch(job_id, connection=redis_conn)
        
        status_map = {
            "queued": "queued",
            "started": "processing",
            "finished": "completed",
            "failed": "failed",
            "deferred": "queued",
            "scheduled": "queued",
        }
        
        return {
            "id": job.id,
            "status": status_map.get(job.get_status(), "unknown"),
            "progress": job.meta.get("progress", 0) if job.get_status() == "started" else (100 if job.is_finished else 0),
            "result": job.result if job.is_finished else None,
            "error": str(job.exc_info) if job.is_failed else None,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "ended_at": job.ended_at.isoformat() if job.ended_at else None,
        }
    except Exception as e:
        return {
            "id": job_id,
            "status": "not_found",
            "error": str(e)
        }


def get_queue_stats() -> dict:
    """Get queue statistics"""
    return {
        "queued": len(processing_queue),
        "active": processing_queue.started_job_registry.count,
        "finished": processing_queue.finished_job_registry.count,
        "failed": processing_queue.failed_job_registry.count,
    }
