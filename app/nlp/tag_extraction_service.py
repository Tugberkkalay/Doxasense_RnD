# app/nlp/tag_extraction_service.py
"""
Automatic tag/keyword extraction using KeyBERT
- Extracts meaningful keywords from text
- Used for search, filtering, and categorization
"""
from typing import List, Set
from keybert import KeyBERT
import re


class TagExtractionService:
    """
    KeyBERT-based automatic tag extraction.
    Extracts semantically meaningful keywords from documents.
    """

    def __init__(self, model_name: str = "BAAI/bge-m3"):
        print(f"[TagExtraction] Initializing KeyBERT with {model_name}...")
        # Use same embedding model as search for consistency
        self.kw_model = KeyBERT(model=model_name)
        
        # Turkish stopwords
        self.stopwords = self._load_stopwords()

    def _load_stopwords(self) -> Set[str]:
        """
        Turkish + English common stopwords
        """
        turkish_stops = {
            "ve", "veya", "ile", "ama", "fakat", "ancak", "bir", "bu", "şu", 
            "o", "bu", "şu", "için", "gibi", "kadar", "daha", "en", "çok",
            "da", "de", "mi", "mı", "mu", "mü", "ki", "ne", "nasıl", "neden",
            "olan", "olarak", "üzere", "sonra", "önce", "arasında", "karşı"
        }
        
        english_stops = {
            "the", "and", "or", "but", "for", "with", "from", "to", "in", 
            "on", "at", "by", "of", "is", "are", "was", "were", "been",
            "have", "has", "had", "this", "that", "these", "those"
        }
        
        return turkish_stops.union(english_stops)

    def extract_tags(
        self, 
        text: str, 
        top_n: int = 10,
        min_length: int = 3
    ) -> List[str]:
        """
        Extract top-N meaningful keywords from text.
        
        Args:
            text: Input text
            top_n: Number of keywords to extract
            min_length: Minimum character length for keywords
        
        Returns:
            List of extracted keywords/tags
        """
        if not text or len(text.strip()) < 50:
            # Too short, fallback to simple extraction
            return self._simple_keyword_extraction(text, top_n)

        try:
            # KeyBERT extraction
            keywords = self.kw_model.extract_keywords(
                text,
                keyphrase_ngram_range=(1, 2),  # 1-2 word phrases
                stop_words=list(self.stopwords),
                top_n=top_n * 2,  # Extract more, then filter
                use_maxsum=True,  # Diversify keywords
                nr_candidates=20,
            )
            
            # Filter and clean
            tags = []
            for kw, score in keywords:
                # Clean keyword
                kw_clean = self._clean_keyword(kw)
                
                # Filter by length and stopwords
                if (len(kw_clean) >= min_length and 
                    kw_clean.lower() not in self.stopwords and
                    score > 0.3):  # Minimum relevance score
                    tags.append(kw_clean)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_tags = []
            for tag in tags:
                tag_lower = tag.lower()
                if tag_lower not in seen:
                    seen.add(tag_lower)
                    unique_tags.append(tag)
            
            return unique_tags[:top_n]
        
        except Exception as e:
            print(f"[TagExtraction] KeyBERT failed: {e}, using fallback")
            return self._simple_keyword_extraction(text, top_n)

    def _clean_keyword(self, keyword: str) -> str:
        """
        Clean and normalize keyword
        """
        # Remove extra whitespace
        kw = " ".join(keyword.split())
        
        # Remove special characters at start/end
        kw = re.sub(r'^[^\w]+|[^\w]+$', '', kw)
        
        # Lowercase
        kw = kw.lower()
        
        return kw

    def _simple_keyword_extraction(self, text: str, top_n: int) -> List[str]:
        """
        Fallback: Simple frequency-based keyword extraction
        """
        if not text:
            return []
        
        # Tokenize
        words = re.findall(r'\b\w{3,}\b', text.lower())
        
        # Filter stopwords
        words = [w for w in words if w not in self.stopwords]
        
        # Count frequency
        from collections import Counter
        word_freq = Counter(words)
        
        # Get top-N
        top_words = [word for word, count in word_freq.most_common(top_n)]
        
        return top_words

    def extract_tags_from_multimodal(
        self,
        full_text: str = "",
        summary: str = "",
        captions: List[str] = None,
        existing_labels: List[str] = None,
        top_n: int = 10
    ) -> List[str]:
        """
        Extract tags from multimodal content (text + captions + labels)
        """
        # Combine all text sources
        text_parts = []
        
        if summary:
            text_parts.append(summary)  # Prioritize summary
        
        if captions:
            text_parts.extend(captions)
        
        if full_text and len(full_text) < 2000:
            text_parts.append(full_text[:1000])
        
        combined_text = " ".join(text_parts)
        
        # Extract tags
        auto_tags = self.extract_tags(combined_text, top_n=top_n)
        
        # Merge with existing labels if any
        if existing_labels:
            all_tags = auto_tags + existing_labels
            # Remove duplicates
            seen = set()
            unique = []
            for tag in all_tags:
                tag_lower = tag.lower()
                if tag_lower not in seen:
                    seen.add(tag_lower)
                    unique.append(tag)
            return unique[:top_n]
        
        return auto_tags
