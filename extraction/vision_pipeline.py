# extraction/vision_pipeline.py
import io
import re
from typing import List, Optional

from PIL import Image
import torch
from transformers import BlipProcessor, BlipForConditionalGeneration

from .schemas import ImageAnalysis


BLIP_MODEL_ID = "Salesforce/blip-image-captioning-base"


class VisionModels:
    def __init__(self, model_id: str = BLIP_MODEL_ID):
        # Cihaz seçimi: önce CUDA, sonra MPS (Apple), en son CPU
        if torch.cuda.is_available():
            self.device = "cuda"
        elif torch.backends.mps.is_available():
            self.device = "mps"
        else:
            self.device = "cpu"

        self.blip_processor = BlipProcessor.from_pretrained(model_id)
        self.blip_model = BlipForConditionalGeneration.from_pretrained(model_id)
        self.blip_model.to(self.device)


class VisionPipeline:
    def __init__(self, vision_models: Optional[VisionModels] = None):
        self.vision = vision_models or VisionModels()

    # --- yardımcılar ---

    def _load_image(self, data: bytes) -> Image.Image:
        return Image.open(io.BytesIO(data)).convert("RGB")

    def _generate_captions(self, image: Image.Image) -> List[str]:
        # Image → BLIP input
        inputs = self.vision.blip_processor(
            images=image,
            return_tensors="pt",
        ).to(self.vision.device)

        with torch.no_grad():
            out = self.vision.blip_model.generate(
                **inputs,
                max_length=64,
                num_beams=4,
            )

        captions = self.vision.blip_processor.batch_decode(
            out,
            skip_special_tokens=True,
        )
        caption = captions[0].strip() if captions else ""
        return [caption] if caption else []

    def _labels_from_caption(self, caption: str, max_labels: int = 5) -> List[str]:
        """
        Çok basit label çıkarımı:
        - caption içindeki kelimeleri al
        - stopword'leri at
        - kısa/önemsiz kelimeleri filtrele
        """
        stopwords = {
            "a", "an", "the", "with", "of", "and", "in", "on", "at",
            "this", "that", "front", "end", "to", "from", "for",
            "there", "is", "are", "car", "vehicle",
        }

        tokens = re.findall(r"[a-zA-Z0-9çğıöşüİĞÖŞÜ]+", caption.lower())
        keywords = [t for t in tokens if t not in stopwords and len(t) > 2]

        # sıralı uniq
        uniq = list(dict.fromkeys(keywords))
        return uniq[:max_labels]

    # --- ana entrypoint ---

    def analyze_image(self, data: bytes, filename: str) -> ImageAnalysis:
        image = self._load_image(data)

        # 1) BLIP caption
        captions = self._generate_captions(image)
        main_caption = captions[0] if captions else ""

        # 2) OCR (şimdilik boş; PDF/image OCR'ı sonra bağlarız)
        ocr_text = ""

        # 3) Caption'dan otomatik label üret
        labels = self._labels_from_caption(main_caption)
        scores = {lbl: 1.0 for lbl in labels}  # şimdilik hepsine 1.0 veriyoruz

        return ImageAnalysis(
            ocr_text=ocr_text,
            clip_top_labels=labels,   # şimdilik CLIP yok, caption → label
            clip_scores=scores,
            blip_captions=captions,
        )
