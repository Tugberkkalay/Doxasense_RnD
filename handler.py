"""
Runpod Serverless Handler
Deploy this to Runpod for GPU-accelerated document processing
"""
import runpod
import os
import tempfile
import requests
import torch
from typing import Dict, Any

# Pre-load models at container startup (CRITICAL for performance!)
print("🚀 Loading AI models...")

# 1. Whisper (Audio transcription)
from transformers import WhisperProcessor, WhisperForConditionalGeneration
whisper_processor = WhisperProcessor.from_pretrained("openai/whisper-large-v3")
whisper_model = WhisperForConditionalGeneration.from_pretrained(
    "openai/whisper-large-v3",
    torch_dtype="auto",
    device_map="auto"
)
print("✓ Whisper-large-v3 loaded")

# 2. BLIP-2 (Image captioning)
from transformers import BlipProcessor, BlipForConditionalGeneration
blip_processor = BlipProcessor.from_pretrained("Salesforce/blip2-opt-2.7b")
blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip2-opt-2.7b")
blip_model.to("cuda" if os.path.exists("/dev/nvidia0") else "cpu")
print("✓ BLIP-2 loaded")

# 3. mT5 (Summarization)
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
mt5_tokenizer = AutoTokenizer.from_pretrained("google/mt5-base")
mt5_model = AutoModelForSeq2SeqLM.from_pretrained("google/mt5-base")
mt5_model.to("cuda" if os.path.exists("/dev/nvidia0") else "cpu")
print("✓ mT5 loaded")

# 4. BGE-M3 (Embeddings)
from sentence_transformers import SentenceTransformer
bge_model = SentenceTransformer("BAAI/bge-m3")
print("✓ BGE-M3 loaded")

# 5. KeyBERT (Tag extraction)
from keybert import KeyBERT
keybert_model = KeyBERT(model=bge_model)
print("✓ KeyBERT loaded")

print("🎉 All models loaded and ready!")


def process_audio(file_path: str) -> Dict[str, Any]:
    """Process audio file with Whisper"""
    import soundfile as sf
    import librosa
    
    # Load audio
    audio, sr = sf.read(file_path)
    if len(audio.shape) > 1:
        audio = audio.mean(axis=1)
    if sr != 16000:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
    
    # Transcribe
    inputs = whisper_processor(audio, sampling_rate=16000, return_tensors="pt")
    inputs = inputs.to(whisper_model.device)
    
    with torch.no_grad():
        predicted_ids = whisper_model.generate(**inputs)
    
    text = whisper_processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
    
    return {
        "text": text,
        "duration": len(audio) / 16000
    }


def process_image(file_path: str) -> Dict[str, Any]:
    """Process image with BLIP-2"""
    from PIL import Image
    
    image = Image.open(file_path).convert("RGB")
    
    # Generate caption
    inputs = blip_processor(images=image, return_tensors="pt")
    inputs = inputs.to(blip_model.device)
    
    with torch.no_grad():
        out = blip_model.generate(**inputs, max_length=64, num_beams=4)
    
    caption = blip_processor.batch_decode(out, skip_special_tokens=True)[0]
    
    return {
        "caption": caption,
        "ocr_text": ""  # Add OCR if needed
    }


def summarize_text(text: str, max_length: int = 150) -> str:
    """Summarize text with mT5"""
    if len(text) < 100:
        return text
    
    inputs = mt5_tokenizer(text[:2000], max_length=512, truncation=True, return_tensors="pt")
    inputs = inputs.to(mt5_model.device)
    
    with torch.no_grad():
        output_ids = mt5_model.generate(**inputs, max_length=max_length, num_beams=2)
    
    summary = mt5_tokenizer.decode(output_ids[0], skip_special_tokens=True)
    return summary


def extract_tags(text: str, top_n: int = 10) -> list:
    """Extract keywords with KeyBERT"""
    if len(text) < 50:
        return []
    
    keywords = keybert_model.extract_keywords(
        text,
        keyphrase_ngram_range=(1, 2),
        top_n=top_n,
        use_maxsum=True
    )
    
    return [kw[0] for kw in keywords]


def generate_embedding(text: str, summary: str, tags: list) -> list:
    """Generate embedding with BGE-M3"""
    # Combine for rich representation
    combined = f"{summary} | {', '.join(tags)}"
    embedding = bge_model.encode(combined, normalize_embeddings=True)
    return embedding.tolist()


def handler(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main Runpod handler
    
    Input:
    {
        "input": {
            "document_id": "uuid",
            "filename": "doc.pdf",
            "mime_type": "application/pdf",
            "file_data": "base64_encoded_file"  # OR file_url
        }
    }
    
    Output:
    {
        "text": "...",
        "summary": "...",
        "tags": [...],
        "embedding": [...],
        "modality": "text|audio|video|image",
        "processing_time": 1.23
    }
    """
    import base64
    
    start_time = time.time()
    
    try:
        job_input = job.get("input", {})
        filename = job_input.get("filename", "")
        mime_type = job_input.get("mime_type", "")
        
        # Get file data (base64 or URL)
        file_data_b64 = job_input.get("file_data")
        file_url = job_input.get("file_url")
        
        if file_data_b64:
            # Decode base64
            file_bytes = base64.b64decode(file_data_b64)
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
                tmp.write(file_bytes)
                file_path = tmp.name
        elif file_url:
            # Download from URL
            response = requests.get(file_url, timeout=60)
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
                tmp.write(response.content)
                file_path = tmp.name
        else:
            return {"error": "No file_data or file_url provided", "status": "failed"}
        
        # Determine modality
        filename_lower = filename.lower()
        text = ""
        captions = []
        metadata = {}
        
        if any(filename_lower.endswith(ext) for ext in ['.mp3', '.wav', '.m4a', '.ogg']):
            # Audio processing
            result = process_audio(file_path)
            text = result["text"]
            modality = "audio"
            metadata = {"duration_seconds": result["duration"]}
            
        elif any(filename_lower.endswith(ext) for ext in ['.mp4', '.mov', '.avi', '.mkv']):
            # Video processing (extract audio first)
            # TODO: Add ffmpeg audio extraction
            modality = "video"
            text = "Video processing not fully implemented"
            
        elif any(filename_lower.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.tif']):
            # Image processing
            result = process_image(file_path)
            text = result["caption"]
            captions = [result["caption"]]
            modality = "image"
            metadata = {"has_text": bool(result.get("ocr_text"))}
            
        else:
            # Text/PDF processing (use simple extraction for now)
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            modality = "text"
        
        # Generate summary
        summary = summarize_text(text) if text else ""
        
        # Extract tags
        tags = extract_tags(text if text else summary, top_n=10)
        
        # Generate embedding
        embedding = generate_embedding(text, summary, tags)
        
        # Clean up
        if file_url and os.path.exists(file_path):
            os.remove(file_path)
        
        processing_time = time.time() - start_time
        
        return {
            "text": text[:5000],  # Limit size
            "summary": summary,
            "tags": tags,
            "labels": [],
            "captions": captions,
            "embedding": embedding,
            "modality": modality,
            "metadata": metadata,
            "processing_time": processing_time
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "status": "failed"
        }


# Start Runpod serverless
if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
