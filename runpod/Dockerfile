# Runpod Serverless GPU Dockerfile
FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy handler
COPY handler.py /app/

# Set environment
ENV PYTHONUNBUFFERED=1
ENV TRANSFORMERS_CACHE=/runpod-volume
ENV HF_HOME=/runpod-volume

# Run handler
CMD ["python", "-u", "/app/handler.py"]
