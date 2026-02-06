"""TF-IDF Similarity Service.

Computes chunk similarity using Term Frequency-Inverse Document Frequency.
Pure Python implementation with no external dependencies, suitable for
corpus sizes up to ~10k documents with < 300ms computation time.
"""

import math
import re
from collections import Counter


class TFIDFService:
    """Compute document similarity using TF-IDF cosine similarity.
    
    This is an on-demand computation — no pre-computed index.
    For corpora > 10k documents, consider migration to sklearn
    or pre-computed embeddings (Ollama).
    """

    def __init__(self) -> None:
        self._stopwords: set[str] = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'can', 'shall',
            'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
            'as', 'into', 'through', 'during', 'before', 'after', 'and',
            'but', 'or', 'nor', 'not', 'so', 'yet', 'both', 'either',
            'neither', 'each', 'every', 'all', 'any', 'few', 'more',
            'most', 'other', 'some', 'such', 'no', 'only', 'own',
            'same', 'than', 'too', 'very', 'just', 'because', 'about',
            'this', 'that', 'these', 'those', 'it', 'its', 'i', 'me',
            'my', 'we', 'our', 'you', 'your', 'he', 'him', 'his',
            'she', 'her', 'they', 'them', 'their', 'what', 'which',
            'who', 'whom', 'when', 'where', 'why', 'how',
        }

    def tokenize(self, text: str) -> list[str]:
        """Tokenize text into lowercase alphanumeric tokens.
        
        Removes stopwords and tokens with 2 or fewer characters.
        
        Args:
            text: Raw text to tokenize.
            
        Returns:
            List of cleaned tokens.
        """
        tokens = re.findall(r'[a-z0-9_]+', text.lower())
        return [t for t in tokens if len(t) > 2 and t not in self._stopwords]

    def compute_tfidf(
        self, documents: list[tuple[str, str]]
    ) -> dict[str, dict[str, float]]:
        """Compute TF-IDF vectors for all documents.
        
        Args:
            documents: List of (doc_id, content) tuples.
            
        Returns:
            Dict mapping doc_id to {term: tfidf_score} vectors.
        """
        if not documents:
            return {}

        # Term frequency per document
        doc_tf: dict[str, Counter] = {}
        for doc_id, content in documents:
            tokens = self.tokenize(content)
            doc_tf[doc_id] = Counter(tokens)

        # Document frequency per term
        n_docs = len(documents)
        df: Counter = Counter()
        for tf in doc_tf.values():
            for term in tf:
                df[term] += 1

        # TF-IDF computation
        tfidf: dict[str, dict[str, float]] = {}
        for doc_id, tf in doc_tf.items():
            total_terms = sum(tf.values())
            if total_terms == 0:
                tfidf[doc_id] = {}
                continue
            tfidf[doc_id] = {
                term: (count / total_terms) * math.log(n_docs / (1 + df[term]))
                for term, count in tf.items()
            }

        return tfidf

    def cosine_similarity(
        self, vec_a: dict[str, float], vec_b: dict[str, float]
    ) -> float:
        """Compute cosine similarity between two TF-IDF vectors.
        
        Args:
            vec_a: First TF-IDF vector.
            vec_b: Second TF-IDF vector.
            
        Returns:
            Cosine similarity score between 0.0 and 1.0.
        """
        common_terms = set(vec_a) & set(vec_b)
        if not common_terms:
            return 0.0

        dot = sum(vec_a[t] * vec_b[t] for t in common_terms)
        mag_a = math.sqrt(sum(v ** 2 for v in vec_a.values()))
        mag_b = math.sqrt(sum(v ** 2 for v in vec_b.values()))

        if mag_a == 0 or mag_b == 0:
            return 0.0

        return dot / (mag_a * mag_b)

    def find_related(
        self,
        target_id: str,
        documents: list[tuple[str, str]],
        top_k: int = 5,
    ) -> list[tuple[str, float, list[str]]]:
        """Find top_k most similar documents to target.
        
        Args:
            target_id: ID of the target document.
            documents: List of (doc_id, content) tuples.
            top_k: Maximum number of related documents to return.
            
        Returns:
            List of (doc_id, similarity_score, shared_terms) tuples,
            sorted by descending similarity.
        """
        if not documents:
            return []

        tfidf = self.compute_tfidf(documents)
        target_vec = tfidf.get(target_id, {})

        if not target_vec:
            return []

        similarities: list[tuple[str, float, list[str]]] = []
        for doc_id, vec in tfidf.items():
            if doc_id == target_id:
                continue
            sim = self.cosine_similarity(target_vec, vec)
            if sim > 0.01:  # Minimum threshold
                common = sorted(
                    (set(target_vec) & set(vec)),
                    key=lambda t: target_vec[t] * vec[t],
                    reverse=True,
                )[:3]
                similarities.append((doc_id, sim, common))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
