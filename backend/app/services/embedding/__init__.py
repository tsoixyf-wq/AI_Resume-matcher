"""Embedding services — BGE model encoding + ChromaDB vector store.

``__all__`` serves as the canonical list of public symbols exported by this
package.  Prefer explicit imports over ``from package import *``.
"""

__all__ = [
    "VectorStore",
    "delete_jd_embedding",
    "delete_resume_embedding",
    "embed_jd",
    "embed_resume",
    "find_similar_resumes",
]
