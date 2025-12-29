# Runpod Serverless GPU Dockerfile
FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install --no-cache-dir \
    runpod \
    transformers \
    accelerate \
    sentence-transformers \
    keybert \
    soundfile \
    librosa \
    pillow \
    requests \
    torch \
    safetensors

# Pre-download models (CRITICAL - bake into image!)
RUN python -c "from transformers import WhisperProcessor, WhisperForConditionalGeneration; \
    WhisperProcessor.from_pretrained('openai/whisper-large-v3'); \
    WhisperForConditionalGeneration.from_pretrained('openai/whisper-large-v3'); \
    print('Whisper downloaded')"

RUN python -c "from transformers import BlipProcessor, BlipForConditionalGeneration; \
    BlipProcessor.from_pretrained('Salesforce/blip2-opt-2.7b'); \
    BlipForConditionalGeneration.from_pretrained('Salesforce/blip2-opt-2.7b'); \
    print('BLIP-2 downloaded')"

RUN python -c "from transformers import AutoTokenizer, AutoModelForSeq2SeqLM; \
    AutoTokenizer.from_pretrained('google/mt5-base'); \
    AutoModelForSeq2SeqLM.from_pretrained('google/mt5-base'); \
    print('mT5 downloaded')"

RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('BAAI/bge-m3'); \
    print('BGE-M3 downloaded')"

# Copy handler
COPY handler.py /app/

# Set Python path
ENV PYTHONUNBUFFERED=1
ENV TRANSFORMERS_CACHE=/runpod-volume/.cache/huggingface

# Run handler
CMD ["python", "-u", "/app/handler.py"]
