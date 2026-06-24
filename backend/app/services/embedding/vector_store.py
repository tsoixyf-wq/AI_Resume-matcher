"""
Vector store wrapper for ChromaDB.
Stores and retrieves resume/JD embeddings for similarity search.
"""

import uuid
from typing import Optional

import chromadb
import structlog
from chromadb.config import Settings as ChromaSettings

from app.core.config import get_settings

logger = structlog.get_logger(__name__)


class VectorStore:
    """ChromaDB-based vector store for resume and JD embeddings."""

    RESUME_COLLECTION = "resumes"
    JD_COLLECTION = "job_descriptions"

    def __init__(self):
        settings = get_settings()
        self._client: chromadb.Client | None = None
        self._host = settings.CHROMA_HOST
        self._port = settings.CHROMA_PORT

    @property
    def client(self) -> chromadb.Client:
        """Lazy-init ChromaDB client."""
        if self._client is None:
            try:
                self._client = chromadb.HttpClient(
                    host=self._host,
                    port=self._port,
                    settings=ChromaSettings(anonymized_telemetry=False),
                )
                logger.info("ChromaDB client connected", host=self._host, port=self._port)
            except Exception:
                logger.warning("ChromaDB HTTP failed, falling back to in-memory")
                self._client = chromadb.Client(
                    Settings(anonymized_telemetry=False, is_persistent=False)
                )
        return self._client

    def get_collection(self, name: str) -> chromadb.Collection:
        """Get or create a collection."""
        try:
            return self.client.get_collection(name)
        except Exception:
            return self.client.create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )

    def upsert_resume(
        self,
        resume_id: uuid.UUID,
        embedding: list[float],
        metadata: dict | None = None,
        text: str = "",
    ) -> str:
        """Store a resume embedding.

        Returns the ChromaDB document ID.
        """
        collection = self.get_collection(self.RESUME_COLLECTION)
        doc_id = str(resume_id)

        collection.upsert(
            ids=[doc_id],
            embeddings=[embedding],
            metadatas=[metadata or {}],
            documents=[text[:5000]],
        )
        logger.debug("Resume embedding stored", resume_id=doc_id)
        return doc_id

    def upsert_jd(
        self,
        jd_id: uuid.UUID,
        embedding: list[float],
        metadata: dict | None = None,
        text: str = "",
    ) -> str:
        """Store a JD embedding."""
        collection = self.get_collection(self.JD_COLLECTION)
        doc_id = str(jd_id)

        collection.upsert(
            ids=[doc_id],
            embeddings=[embedding],
            metadatas=[metadata or {}],
            documents=[text[:5000]],
        )
        logger.debug("JD embedding stored", jd_id=doc_id)
        return doc_id

    def query_similar_resumes(
        self,
        query_embedding: list[float],
        n_results: int = 10,
    ) -> list[dict]:
        """Find resumes most similar to a query (JD) embedding."""
        collection = self.get_collection(self.RESUME_COLLECTION)
        if collection.count() == 0:
            return []

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, collection.count()),
            include=["metadatas", "documents", "distances"],
        )

        return [
            {
                "id": results["ids"][0][i],
                "metadata": results["metadatas"][0][i] if results["metadatas"][0] else {},
                "distance": results["distances"][0][i],
            }
            for i in range(len(results["ids"][0]))
        ]

    def delete_resume(self, resume_id: uuid.UUID):
        """Remove a resume embedding."""
        collection = self.get_collection(self.RESUME_COLLECTION)
        try:
            collection.delete(ids=[str(resume_id)])
        except Exception:
            pass

    def delete_jd(self, jd_id: uuid.UUID):
        """Remove a JD embedding."""
        collection = self.get_collection(self.JD_COLLECTION)
        try:
            collection.delete(ids=[str(jd_id)])
        except Exception:
            pass

    def count(self, collection_name: str) -> int:
        """Get the number of documents in a collection."""
        collection = self.get_collection(collection_name)
        return collection.count()
