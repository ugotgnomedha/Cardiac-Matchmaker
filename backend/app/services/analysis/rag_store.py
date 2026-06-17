"""Platform plumbing for the RAG: persist chunks to Postgres + vectors to Qdrant, and load a retriever."""

import os
from uuid import UUID, uuid4

import numpy as np

from app.services.analysis.rag import (
    Chunk,
    Embedder,
    LiteratureRetriever,
    SentenceTransformerEmbedder,
    chunk_pages,
    extract_pages,
)

QDRANT_URL = os.getenv("QDRANT_URL", "http://vector-db:6333")
COLLECTION = os.getenv("QDRANT_COLLECTION", "document_chunks")


class QdrantVectorStore:
    """Minimal Qdrant wrapper: ensure a cosine collection, upsert, and scroll vectors."""

    def __init__(self, url: str = QDRANT_URL, collection: str = COLLECTION):
        """Record the Qdrant URL and collection; the client connects on first use."""
        self.url = url
        self.collection = collection
        self._client = None

    @property
    def client(self):
        """The Qdrant client, connected on first access."""
        if self._client is None:
            from qdrant_client import QdrantClient

            self._client = QdrantClient(url=self.url)
        return self._client

    def ensure_collection(self, dim: int) -> None:
        """Create the cosine collection at the given dimension if it does not exist."""
        from qdrant_client.models import Distance, VectorParams

        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )

    def upsert(self, ids: list[str], vectors: np.ndarray, payloads: list[dict]) -> None:
        """Upsert points (id, vector, payload) into the collection."""
        from qdrant_client.models import PointStruct

        points = [
            PointStruct(id=i, vector=v.tolist(), payload=p)
            for i, v, p in zip(ids, vectors, payloads)
        ]
        self.client.upsert(collection_name=self.collection, points=points)

    def vectors_for_project(self, project_id: UUID) -> dict[str, list[float]]:
        """All chunk vectors for a project, keyed by point id (the chunk's vector_id)."""
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        flt = Filter(
            must=[FieldCondition(key="project_id", match=MatchValue(value=str(project_id)))]
        )
        out: dict[str, list[float]] = {}
        offset = None
        while True:
            points, offset = self.client.scroll(
                collection_name=self.collection,
                scroll_filter=flt,
                with_vectors=True,
                with_payload=False,
                limit=256,
                offset=offset,
            )
            for point in points:
                out[str(point.id)] = point.vector  # pyrefly: ignore
            if offset is None:
                break
        return out


    def delete_by_document(self, document_id: str) -> None:
        """Delete all vectors for a document from Qdrant."""
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        self.client.delete(
            collection_name=self.collection,
            points_selector=Filter(
                must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
            ),
        )


class LiteratureIndexer:
    """Chunk a document's PDF into DocumentChunk rows and Qdrant vectors."""

    def __init__(self, embedder: Embedder | None = None, store: QdrantVectorStore | None = None):
        """Use the given embedder/store, defaulting to MiniLM + Qdrant."""
        self.embedder = embedder or SentenceTransformerEmbedder()
        self.store = store or QdrantVectorStore()

    def index_document(self, document) -> int:
        """Chunk, embed, and persist a document; return the chunk count."""
        from app.models.base.base_model import db
        from app.models.document.document_model import DocumentChunk

        chunks = chunk_pages(extract_pages(document.storage_path), document_id=str(document.id))
        if not chunks:
            document.status = "indexed"
            document.save()
            return 0

        vectors = self.embedder.encode([c.text for c in chunks])
        self.store.ensure_collection(int(vectors.shape[1]))

        ids: list[str] = []
        payloads: list[dict] = []
        with db.atomic():
            for chunk in chunks:
                chunk_id = uuid4()
                DocumentChunk.create(
                    id=chunk_id,
                    document=document,
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page,
                    text=chunk.text,
                    vector_id=str(chunk_id),
                    metadata={"page": chunk.page},
                )
                ids.append(str(chunk_id))
                payloads.append(
                    {
                        "project_id": str(document.project_id),
                        "document_id": str(document.id),
                        "chunk_index": chunk.chunk_index,
                        "page": chunk.page,
                    }
                )
            document.status = "indexed"
            document.save()

        self.store.upsert(ids, vectors, payloads)
        return len(chunks)


def load_retriever(
    project_id: UUID,
    embedder: Embedder | None = None,
    store: QdrantVectorStore | None = None,
) -> LiteratureRetriever:
    """Rebuild a retriever for a project from its persisted chunks + Qdrant vectors."""
    from app.models.document.document_model import Document, DocumentChunk

    embedder = embedder or SentenceTransformerEmbedder()
    store = store or QdrantVectorStore()

    rows = list(
        DocumentChunk.select(DocumentChunk, Document)
        .join(Document)
        .where(Document.project == project_id)
        .order_by(DocumentChunk.document, DocumentChunk.chunk_index)
    )
    vectors_by_id = store.vectors_for_project(project_id)

    chunks: list[Chunk] = []
    vectors: list[list[float]] = []
    for row in rows:
        vector = vectors_by_id.get(str(row.vector_id))
        if vector is None:
            continue
        chunks.append(
            Chunk(
                text=row.text,
                page=row.page_number or 0,
                chunk_index=row.chunk_index,
                chunk_id=str(row.id),
                document_id=str(row.document_id),
            )
        )
        vectors.append(vector)

    return LiteratureRetriever(chunks, np.asarray(vectors, dtype=np.float32), embedder)
