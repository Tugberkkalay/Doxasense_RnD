# app/summarization/service.py
from __future__ import annotations
from typing import List

import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM


class SummarizationService:
    def __init__(
        self,
        model_name: str = "google/mt5-base",  # Multilingual, better Turkish support
        max_input_tokens: int = 512,   # mT5 için optimize
        max_summary_tokens: int = 150,
        device: str | None = None,
    ):
        self.model_name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device
        self.model.to(self.device)

        self.max_input_tokens = max_input_tokens
        self.max_summary_tokens = max_summary_tokens

    def _chunk_text(self, text: str) -> List[str]:
        # Çok kaba: paragraf bazlı kırpma + token sınırı
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        chunks: List[str] = []
        current = ""

        for p in paragraphs:
            candidate = (current + "\n" + p).strip() if current else p
            tokens = self.tokenizer(
                candidate,
                truncation=False,
                add_special_tokens=False,
                return_tensors=None,
            )["input_ids"]
            if len(tokens) <= self.max_input_tokens:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                # paragraf tek başına bile uzunsa, doğrudan truncate edelim
                if len(tokens) > self.max_input_tokens:
                    truncated = self.tokenizer.decode(
                        tokens[: self.max_input_tokens],
                        skip_special_tokens=True,
                        clean_up_tokenization_spaces=True,
                    )
                    chunks.append(truncated)
                    current = ""
                else:
                    current = p

        if current:
            chunks.append(current)

        return chunks or [text]

    def _summarize_chunk(self, chunk: str) -> str:
        inputs = self.tokenizer(
            chunk,
            max_length=self.max_input_tokens,
            truncation=True,
            return_tensors="pt",
        ).to(self.device)

        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs,
                max_length=self.max_summary_tokens,
                num_beams=2,            # 4 yerine 2 → daha hızlı
                early_stopping=True,
                no_repeat_ngram_size=3,
            )

        summary = self.tokenizer.decode(
            output_ids[0],
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        )
        return summary.strip()

    def summarize(self, text: str) -> str:
        if not text:
            return ""

        text = text.strip()

        # Çok uç durumları hard truncate edelim
        if len(text) > 15000:
            text = text[:15000]

        chunks = self._chunk_text(text)
        summaries: List[str] = []
        for ch in chunks:
            try:
                s = self._summarize_chunk(ch)
                if s:
                    summaries.append(s)
            except Exception as e:
                print("[Summarizer] chunk error:", e)

        full_summary = "\n".join(summaries).strip()
        return full_summary or text[:1000]
