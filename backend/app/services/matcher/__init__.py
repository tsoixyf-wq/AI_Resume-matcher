"""Matching pipeline services.

Submodules are imported explicitly via full paths (e.g.
``from app.services.matcher.rule_matcher import RuleMatcher``) to avoid
eagerly loading heavy ML dependencies (sentence_transformers, torch) at
package import time.

``__all__`` serves as the canonical list of public symbols exported by this
package.  Prefer explicit imports over ``from package import *``.
"""

__all__ = [
    "LLMMatcher",
    "RuleMatcher",
    "SemanticMatcher",
    "TFIDFMatcher",
    "compute_weighted_score",
]
