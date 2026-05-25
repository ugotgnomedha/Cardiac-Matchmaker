"""Unit tests for RAG retrieval (chunking, dense/BM25/hybrid, lookups) with a fake embedder."""

import numpy as np

from app.services.analysis.rag import (
    Chunk,
    LiteratureRetriever,
    chunk_pages,
    clean,
)


class FakeEmbedder:
    """Deterministic bag-of-words embedder so dense scores track word overlap."""

    def __init__(self, corpus: list[str]):
        """Build the vocabulary from the corpus."""
        vocab = sorted({tok for text in corpus for tok in text.lower().split()})
        self.index = {tok: i for i, tok in enumerate(vocab)}

    def encode(self, texts: list[str]) -> np.ndarray:
        """Encode texts as L2-normalised term-frequency vectors over the vocabulary."""
        out = np.zeros((len(texts), len(self.index)), dtype=np.float32)
        for row, text in enumerate(texts):
            for tok in text.lower().split():
                if tok in self.index:
                    out[row, self.index[tok]] += 1.0
            norm = np.linalg.norm(out[row])
            if norm:
                out[row] /= norm
        return out


CHUNK_TEXTS = [
    "COL1A1 collagen provides tensile strength to the extracellular matrix",
    "FN1 fibronectin mediates cell adhesion in connective tissue",
    "proteins were quantified by mass spectrometry in this study",
]


def _retriever() -> LiteratureRetriever:
    """Build a retriever over the fixed CHUNK_TEXTS with the fake embedder."""
    chunks = [Chunk(text=t, page=i + 1, chunk_index=i) for i, t in enumerate(CHUNK_TEXTS)]
    embedder = FakeEmbedder(CHUNK_TEXTS)
    vectors = embedder.encode(CHUNK_TEXTS)
    return LiteratureRetriever(chunks, vectors, embedder)


def test_clean_fixes_ligatures_and_linebreaks():
    """clean() repairs ligatures and hyphenated line breaks."""
    assert clean("ﬁbrin") == "fibrin"
    assert clean("extra-\ncellular   matrix") == "extracellular matrix"


def test_chunk_pages_tracks_page_and_index():
    """Chunks carry contiguous indices, their page number, and the document id."""
    pages = ["alpha beta " * 120, "gamma delta epsilon"]
    chunks = chunk_pages(pages, document_id="doc-1")
    assert chunks[0].page == 1
    assert chunks[-1].page == 2
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    assert all(c.document_id == "doc-1" for c in chunks)
    assert sum(c.page == 1 for c in chunks) >= 2


def test_dense_bm25_and_hybrid_rank_relevant_chunk_first():
    """Every retrieval mode ranks the most relevant chunk first."""
    retriever = _retriever()
    for mode in ("dense", "bm25", "hybrid"):
        top = retriever.search("collagen tensile strength", k=3, mode=mode)
        assert top[0].chunk_index == 0, mode
        assert top[0].page == 1


def test_lookup_protein_finds_literal_mentions():
    """lookup_protein returns only chunks that literally mention the symbol."""
    hits = _retriever().lookup_protein("FN1")
    assert [h.page for h in hits] == [2]


def test_protein_function_only_returns_mentioning_chunks():
    """protein_function returns mentioning chunks only, and nothing for an absent gene."""
    retriever = _retriever()
    hits = retriever.protein_function("COL1A1")
    assert len(hits) == 1
    assert hits[0].page == 1
    assert retriever.protein_function("ABSENTGENE") == []
