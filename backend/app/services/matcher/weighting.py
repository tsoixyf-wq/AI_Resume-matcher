"""
Shared weighting logic for the matching pipeline.
Centralizes all weight configurations so api/matching.py and match_agent.py
use the same calculation.

Weight configurations are documented in CLAUDE.md:
- With LLM + semantic:  rule=0.10, tfidf=0.20, semantic=0.35, llm=0.35
- With LLM, no semantic: rule=0.10, tfidf=0.20, semantic=0.00, llm=0.70
- No LLM + semantic:     rule=0.20, tfidf=0.35, semantic=0.45
- No LLM, no semantic:   rule=0.25, tfidf=0.75, semantic=0.00
"""

from app.schemas.matching import DimensionScores


def compute_weighted_score(
    rule_score: float,
    tfidf_score: float,
    semantic_score: float,
    llm_result: dict | None,
) -> tuple[float, DimensionScores, str]:
    """
    Compute the weighted overall score from all matching stages.

    Args:
        rule_score: Stage 1 rule-matching score (0-10)
        tfidf_score: Stage 2 TF-IDF score (0-10)
        semantic_score: Stage 3 semantic similarity score (0-10)
        llm_result: Stage 4 LLM reasoning result dict, or None if LLM disabled.
                    Expected keys: score, dimension_scores, matched_skills,
                    missing_skills, reasoning, suggestions.

    Returns:
        (overall_score, dimension_scores, source) where *source* is a string
        label identifying which weight configuration was applied:
        - "llm+semantic" when LLM is enabled (regardless of semantic availability)
        - "semantic_only" when LLM is disabled
    """
    semantic_available = semantic_score > 0

    if llm_result:
        if semantic_available:
            weights = {"rule": 0.10, "tfidf": 0.20, "semantic": 0.35, "llm": 0.35}
        else:
            weights = {"rule": 0.10, "tfidf": 0.20, "semantic": 0.0, "llm": 0.70}
        source = "llm+semantic"
        overall = (
            weights["rule"] * rule_score
            + weights["tfidf"] * tfidf_score
            + weights["semantic"] * semantic_score
            + weights["llm"] * llm_result["score"]
        )
        dim_data = llm_result["dimension_scores"]
        dim_scores = DimensionScores(
            education=dim_data.get("education", 5.0),
            skills=dim_data.get("skills", 5.0),
            experience=dim_data.get("experience", 5.0),
            certifications=dim_data.get("certifications", 5.0),
            languages=dim_data.get("languages", 5.0),
            location=dim_data.get("location", 5.0),
            overall=round(overall, 1),
        )
    else:
        if semantic_available:
            weights = {"rule": 0.20, "tfidf": 0.35, "semantic": 0.45}
        else:
            weights = {"rule": 0.25, "tfidf": 0.75, "semantic": 0.0}
        source = "semantic_only"
        overall = (
            weights["rule"] * rule_score
            + weights["tfidf"] * tfidf_score
            + weights["semantic"] * semantic_score
        )
        dim_scores = DimensionScores(overall=round(overall, 1))

    return round(overall, 1), dim_scores, source
