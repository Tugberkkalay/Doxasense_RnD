# app/queue.py
import os
from redis import Redis
from rq import Queue

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_NAME = os.getenv("RQ_QUEUE_NAME", "doxasense_mind")

redis_conn = Redis.from_url(REDIS_URL)
task_queue = Queue(QUEUE_NAME, connection=redis_conn)
