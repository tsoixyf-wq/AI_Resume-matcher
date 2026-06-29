"""Resume parsing services.

Submodules are imported explicitly via full paths (e.g.
``from app.services.parser.document_loader import DocumentLoader``) to avoid
eagerly loading heavy ML dependencies (sentence_transformers, spaCy, GLiNER)
at package import time.

``__all__`` serves as the canonical list of public symbols exported by this
package.  Prefer explicit imports over ``from package import *``.
"""

__all__ = [
    "DocumentLoader",
    "LanguageDetector",
    "LLMExtractor",
    "NERExtractor",
    "ParseResult",
    "ResumeParserService",
    "SkillNormalizer",
    "classify_resume",
]
