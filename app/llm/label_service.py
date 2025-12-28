# app/llm/label_service.py
from typing import List, Optional

import os
import json

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class LabelService:
    """
    NormalizedDoc benzeri bir içerikten semantik etiket üretir.
    Varsayılan: OpenAI kullanır. İstersen use_remote_api=False ile sadece
    basit rule-based fallback kullanabilirsin.
    """

    def __init__(self, use_remote_api: bool = True, max_labels: int = 10):
        self.use_remote_api = use_remote_api and (OpenAI is not None)
        self.max_labels = max_labels

        self.client: Optional[OpenAI] = None
        if self.use_remote_api:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                # API key yoksa remote kapat
                self.use_remote_api = False
            else:
                self.client = OpenAI(api_key=api_key)

    # ----------------- Public API ----------------- #
    def generate_labels(
        self,
        main_text: str,
        summary_text: str = "",
        captions: Optional[List[str]] = None,
    ) -> List[str]:
        captions = captions or []

        # Boş içerik ise label üretme
        if not main_text and not summary_text and not captions:
            return []

        # LLM varsa onu dene, olmazsa rule-based fallback
        if self.use_remote_api and self.client is not None:
            try:
                return self._generate_labels_llm(main_text, summary_text, captions)
            except Exception:
                # Prod’da loglanır; Ar-Ge’de sorun değil
                pass

        return self._generate_labels_fallback(main_text, summary_text, captions)

    # ----------------- LLM tabanlı ----------------- #
    def _generate_labels_llm(
        self,
        main_text: str,
        summary_text: str,
        captions: List[str],
    ) -> List[str]:
        """
        OpenAI üzerinden JSON array dönen etiketler.
        """
        content_preview = (summary_text or main_text)[:2000]
        captions_joined = "; ".join(captions)[:500]

        prompt = f"""
Aşağıda kurumsal bir içerik özeti var. Görevin:

- Bu içeriğe göre ARAMADA kullanılabilecek kısa ve anlamlı etiketler üretmek.
- Etiketler 1-3 kelime uzunluğunda olmalı (ör. "iş güvenliği", "müşteri şikayeti").
- Türkçe üret.
- Sadece JSON array döndür. Örnek: ["iş güvenliği", "toplantı notu"]

İçerik Özeti:
---
{content_preview}
---

Ek Görsel Caption'lar:
---
{captions_joined}
---
"""

        resp = self.client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            response_format={"type": "json_object"},
        )

        raw = resp.output[0].content[0].text
        data = json.loads(raw)

        # Beklenen: {"labels": ["foo", "bar"]}
        labels = data.get("labels")
        if not isinstance(labels, list):
            # Eğer doğrudan array dönerse:
            if isinstance(data, list):
                labels = data
            else:
                return []

        # Normalize: string olmayanları at, kısalt
        cleaned = []
        for lbl in labels:
            if not isinstance(lbl, str):
                continue
            lbl = lbl.strip()
            if not lbl:
                continue
            cleaned.append(lbl)

        # Unique + limit
        uniq = list(dict.fromkeys(cleaned))
        return uniq[: self.max_labels]

    # ----------------- Fallback (rule-based) ----------------- #
    def _generate_labels_fallback(
        self,
        main_text: str,
        summary_text: str,
        captions: List[str],
    ) -> List[str]:
        """
        LLM yoksa çok basit keyword extraction.
        """
        import re

        text = " ".join(
            part for part in [summary_text, main_text, " ".join(captions)] if part
        )

        stopwords = {
            "ve", "veya", "ile", "ama", "fakat", "ancak",
            "the", "and", "of", "for", "to", "in", "on",
            "bir", "bu", "şu", "da", "de", "için",
        }

        tokens = re.findall(r"[a-zA-Z0-9çğıöşüİĞÖŞÜ]+", text.lower())
        keywords = [t for t in tokens if t not in stopwords and len(t) > 3]

        uniq = list(dict.fromkeys(keywords))
        return uniq[: self.max_labels]
