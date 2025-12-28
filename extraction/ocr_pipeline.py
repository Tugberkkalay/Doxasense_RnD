# extraction/ocr_pipeline.py
import io
from typing import List

import pdfplumber
from pdf2image import convert_from_bytes
from PIL import Image
import pytesseract
import docx

from .schemas import ExtractedText


class OcrPipeline:
    def __init__(self, tesseract_lang: str = "tur+eng"):
        """
        tesseract_lang: 'tur', 'tur+eng' gibi.
        Tesseract binary sistemde kurulu olmalı.
        """
        self.tesseract_lang = tesseract_lang

    # --------- İç yardımcılar --------- #
    def _extract_pdf_text(self, data: bytes) -> List[str]:
        """PDF'ten native text çekmeye çalışır."""
        pages_text = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages_text.append(text)
        return pages_text

    def _extract_scanned_pdf_ocr(self, data: bytes) -> List[str]:
        """PDF sayfalarını image'e çevirip Tesseract ile OCR yapar."""
        images = convert_from_bytes(data)
        pages_text = []
        for img in images:
            text = pytesseract.image_to_string(img, lang=self.tesseract_lang)
            pages_text.append(text)
        return pages_text

    def _extract_docx_text(self, data: bytes) -> str:
        file_like = io.BytesIO(data)
        document = docx.Document(file_like)
        return "\n".join(p.text for p in document.paragraphs)

    def _extract_txt(self, data: bytes) -> str:
        return data.decode("utf-8", errors="ignore")

    def _extract_image_ocr(self, data: bytes) -> str:
        img = Image.open(io.BytesIO(data)).convert("RGB")
        text = pytesseract.image_to_string(img, lang=self.tesseract_lang)
        return text

    # --------- Public API --------- #
    def extract_from_pdf(self, data: bytes) -> ExtractedText:
        # 1) Normal PDF text’i dene
        pages_text = self._extract_pdf_text(data)
        full_text = "\n".join(pages_text).strip()

        # 2) Çok boşsa taranmış pdf kabul et → OCR
        if len(full_text) < 50:  # kaba eşik
            pages_text = self._extract_scanned_pdf_ocr(data)
            full_text = "\n".join(pages_text).strip()
            source_type = "scanned_pdf"
        else:
            source_type = "pdf"

        return ExtractedText(
            text=full_text,
            language="tr",
            source_type=source_type,
            pages=pages_text,
        )

    def extract_from_docx(self, data: bytes) -> ExtractedText:
        text = self._extract_docx_text(data)
        return ExtractedText(
            text=text,
            language="tr",
            source_type="docx",
            pages=None,
        )

    def extract_from_image(self, data: bytes) -> ExtractedText:
        text = self._extract_image_ocr(data)
        return ExtractedText(
            text=text,
            language="tr",
            source_type="image",
            pages=None,
        )

    def extract_from_txt(self, data: bytes) -> ExtractedText:
        text = self._extract_txt(data)
        return ExtractedText(
            text=text,
            language="tr",
            source_type="txt",
            pages=None,
        )

    def auto_extract(self, filename: str, data: bytes) -> ExtractedText:
        name = filename.lower()
        if name.endswith(".pdf"):
            return self.extract_from_pdf(data)
        elif name.endswith(".docx"):
            return self.extract_from_docx(data)
        elif name.endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff")):
            return self.extract_from_image(data)
        else:
            return self.extract_from_txt(data)

    def extract_text(self, data: bytes, filename: str) -> ExtractedText:
        """
        Geriye dönük uyumluluk için küçük wrapper.
        ingest_auto şu imza ile çağırıyor: extract_text(data, filename)
        Biz içeride auto_extract(filename, data) kullanıyoruz.
        """
        return self.auto_extract(filename, data)