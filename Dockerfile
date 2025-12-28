# Doxasense-Mind / Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Sistem paketleri (ffmpeg, tesseract, poppler vs.)
RUN apt-get update && apt-get install -y \
    build-essential \
    ffmpeg \
    libsndfile1 \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-tur \
    tesseract-ocr-eng \
    git \
    && rm -rf /var/lib/apt/lists/*

# Python bağımlılıkları
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodu
COPY . .

ENV PYTHONUNBUFFERED=1

# Default komut: API
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
