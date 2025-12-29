# Runpod Serverless GPU Dockerfile
FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better caching)
COPY requirements.txt /app/

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download models (CRITICAL - bake into image!)
RUN echo "Downloading Whisper-large-v3..." && \
    python -c "from transformers import WhisperProcessor, WhisperForConditionalGeneration; \
    WhisperProcessor.from_pretrained('openai/whisper-large-v3'); \
    WhisperForConditionalGeneration.from_pretrained('openai/whisper-large-v3'); \
    print('✓ Whisper downloaded')"

RUN echo "Downloading BLIP-2..." && \
    python -c "from transformers import BlipProcessor, BlipForConditionalGeneration; \
    BlipProcessor.from_pretrained('Salesforce/blip2-opt-2.7b'); \
    BlipForConditionalGeneration.from_pretrained('Salesforce/blip2-opt-2.7b'); \
    print('✓ BLIP-2 downloaded')"

RUN echo "Downloading mT5..." && \
    python -c "from transformers import AutoTokenizer, AutoModelForSeq2SeqLM; \
    AutoTokenizer.from_pretrained('google/mt5-base'); \
    AutoModelForSeq2SeqLM.from_pretrained('google/mt5-base'); \
    print('✓ mT5 downloaded')"

RUN echo "Downloading BGE-M3..." && \
    python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('BAAI/bge-m3'); \
    print('✓ BGE-M3 downloaded')"

# Copy handler
COPY handler.py /app/

# Set environment
ENV PYTHONUNBUFFERED=1
ENV TRANSFORMERS_CACHE=/runpod-volume/.cache/huggingface

# Run handler
CMD ["python", "-u", "/app/handler.py"]
