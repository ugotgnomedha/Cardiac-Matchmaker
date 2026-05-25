"""Literature RAG over a project's documents: chunking, embedding, and dense/BM25/hybrid retrieval."""

import os
import re
from dataclasses import dataclass
from typing import Optional, Protocol

import numpy as np

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
WORDS_PER_CHUNK = 180
WORD_OVERLAP = 40

_LIGATURES = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl", "ﬆ": "st"}


def _tok(text: str) -> list[str]:
    """Lowercase alphanumeric tokens for BM25."""
    return [w for w in re.split(r"[^a-z0-9]+", text.lower()) if len(w) >= 2]


def clean(text: str) -> str:
    """Fix ligatures, join hyphenated line breaks, and collapse whitespace."""
    for lig, rep in _LIGATURES.items():
        text = text.replace(lig, rep)
    text = re.sub(r"-\n(?=\w)", "", text)
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class Chunk:
    """One passage of a document, with its page and (once persisted) its ids."""

    text: str
    page: int
    chunk_index: int
    chunk_id: Optional[str] = None
    document_id: Optional[str] = None


@dataclass
class Hit:
    """A retrieved passage: page number, score, text, and source ids for citation."""

    page: int
    score: float
    text: str
    chunk_index: int
    chunk_id: Optional[str] = None
    document_id: Optional[str] = None


def extract_pages(pdf_path: str) -> list[str]:
    """Extract and clean text for each PDF page (lazy pypdf import)."""
    from pypdf import PdfReader

    reader = PdfReader(pdf_path)
    return [clean(p.extract_text() or "") for p in reader.pages]


def chunk_pages(pages: list[str], document_id: Optional[str] = None) -> list[Chunk]:
    """Per-page sliding window over words, keeping each chunk's page number."""
    chunks: list[Chunk] = []
    step = WORDS_PER_CHUNK - WORD_OVERLAP
    for page_no, text in enumerate(pages, start=1):
        words = text.split()
        if not words:
            continue
        for start in range(0, len(words), step):
            piece = words[start : start + WORDS_PER_CHUNK]
            if len(piece) < 20 and start > 0:
                break
            chunks.append(
                Chunk(
                    text=" ".join(piece),
                    page=page_no,
                    chunk_index=len(chunks),
                    document_id=document_id,
                )
            )
            if start + WORDS_PER_CHUNK >= len(words):
                break
    return chunks


class Embedder(Protocol):
    """Encodes texts into L2-normalised vectors."""

    def encode(self, texts: list[str]) -> np.ndarray:
        """Return one normalised vector per input text."""
        ...


class SentenceTransformerEmbedder:
    """MiniLM embeddings (lazy import so the model is only loaded when used)."""

    def __init__(self, model_name: str = MODEL_NAME):
        """Record the model name; the model itself loads on first use."""
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        """The underlying SentenceTransformer, loaded on first access."""
        if self._model is None:
            os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(self, texts: list[str]) -> np.ndarray:
        """Embed texts into normalised float32 vectors."""
        return self.model.encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        ).astype(np.float32)


class LiteratureRetriever:
    """Dense / BM25 / hybrid retrieval over a fixed set of chunks + their vectors."""

    def __init__(self, chunks: list[Chunk], vectors: np.ndarray, embedder: Embedder):
        """Hold the chunks, their vectors, and the embedder used for queries."""
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must be the same length")
        self.chunks = chunks
        self.vectors = np.asarray(vectors, dtype=np.float32)
        self.embedder = embedder
        self._bm25 = None

    @property
    def bm25(self):
        """Lazily built BM25 index over the chunk texts."""
        if self._bm25 is None:
            from rank_bm25 import BM25Okapi

            self._bm25 = BM25Okapi([_tok(c.text) for c in self.chunks])
        return self._bm25

    def _dense_scores(self, query: str) -> np.ndarray:
        """Cosine similarity of the query to every chunk vector."""
        q = self.embedder.encode([query])[0].astype(np.float32)
        with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
            return self.vectors @ q

    def _bm25_scores(self, query: str) -> np.ndarray:
        """BM25 score of the query against every chunk."""
        return np.asarray(self.bm25.get_scores(_tok(query)))

    def _rrf(self, query: str, K: int = 60) -> tuple[list[int], dict[int, float]]:
        """Reciprocal-rank fusion of dense and BM25 into (ordered indices, scores)."""
        fused: dict[int, float] = {}
        for scores in (self._dense_scores(query), self._bm25_scores(query)):
            for rank, i in enumerate(np.argsort(scores)[::-1]):
                fused[int(i)] = fused.get(int(i), 0.0) + 1.0 / (K + rank)
        return sorted(fused, key=lambda i: -fused[i]), fused

    def _hit(self, i: int, score: float) -> Hit:
        """Build a Hit for chunk index ``i`` with the given score."""
        c = self.chunks[i]
        return Hit(c.page, round(float(score), 4), c.text, c.chunk_index, c.chunk_id, c.document_id)

    def search(self, query: str, k: int = 5, mode: Optional[str] = None) -> list[Hit]:
        """Top-k passages for a query (mode: dense, bm25, or hybrid)."""
        mode = mode or os.environ.get("RAG_RETRIEVAL", "hybrid")
        if not self.chunks:
            return []
        if mode == "hybrid":
            order, fused = self._rrf(query)
            return [self._hit(i, fused[i]) for i in order[:k]]
        scores = self._dense_scores(query) if mode == "dense" else self._bm25_scores(query)
        order = np.argsort(scores)[::-1][:k]
        return [self._hit(i, scores[i]) for i in order]

    def lookup_protein(self, name: str, k: int = 5) -> list[Hit]:
        """Passages that literally mention a gene/protein symbol."""
        pat = re.compile(rf"\b{re.escape(name)}\b", re.IGNORECASE)
        return [self._hit(i, 1.0) for i, c in enumerate(self.chunks) if pat.search(c.text)][:k]

    def protein_function(self, name: str, k: int = 4) -> list[Hit]:
        """Mentioning passages for a protein, ranked by similarity to a function query."""
        pat = re.compile(rf"\b{re.escape(name)}\b", re.IGNORECASE)
        mentions = [i for i, c in enumerate(self.chunks) if pat.search(c.text)]
        if not mentions:
            return []
        q = f"biomechanical function and structural role of {name} protein in heart tissue"
        sims = self._dense_scores(q)
        ranked = sorted(mentions, key=lambda i: sims[i], reverse=True)
        return [self._hit(i, sims[i]) for i in ranked[:k]]
