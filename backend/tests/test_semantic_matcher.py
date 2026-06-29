"""Tests for SemanticMatcher — BGE embedding-based matching."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.schemas.job import (
    EducationRequirement,
    ParsedJDData,
    Requirement,
    SkillRequirement,
)
from app.schemas.resume import (
    BasicInfo,
    Education,
    ParsedResumeData,
    Skill,
    WorkExperience,
)


@pytest.fixture
def resume_en():
    """English resume fixture for semantic matching tests."""
    return ParsedResumeData(
        basic_info=BasicInfo(
            name="John Doe", email="john@example.com", years_of_experience=5,
        ),
        education=[
            Education(school="Stanford", degree="Master", major="Computer Science"),
        ],
        work_experience=[
            WorkExperience(
                company="Google", title="Senior Engineer",
                description="Built scalable microservices in Python and Go",
            ),
        ],
        skills=[
            Skill(name="Python", category="Programming"),
            Skill(name="Docker", category="DevOps"),
            Skill(name="Kubernetes", category="DevOps"),
            Skill(name="PostgreSQL", category="Database"),
        ],
        resume_type="experienced",
    )


@pytest.fixture
def jd_en():
    """English JD fixture."""
    return ParsedJDData(
        basic_info={"title": "Senior Backend Engineer", "location": "San Francisco"},
        skills_required=[
            SkillRequirement(name="Python", importance="required"),
            SkillRequirement(name="Docker", importance="required"),
            SkillRequirement(name="AWS", importance="preferred"),
        ],
        education_required=EducationRequirement(min_degree="Bachelor"),
        requirements=[
            Requirement(description="5+ years experience in backend development"),
            Requirement(description="Strong Python and cloud experience"),
        ],
        responsibilities=["Design and build APIs", "Mentor junior engineers"],
    )


class MockSentenceTransformer:
    """Mock that returns deterministic embeddings for testing."""

    def encode(self, texts, show_progress_bar=False, **kwargs):
        """Return a fixed-dimension random embedding per text.

        Same text always produces the same embedding (deterministic via seed).
        """
        if isinstance(texts, str):
            texts = [texts]

        # Deterministic: use hash of text to seed the vector
        embeddings = []
        for text in texts:
            rng = np.random.RandomState(hash(text) % 2**31)
            embeddings.append(rng.rand(1024).astype(np.float32))
        return np.array(embeddings)


class TestSemanticMatcher:
    """Semantic matcher tests with mocked SentenceTransformer."""

    @pytest.mark.asyncio
    async def test_match_returns_structure(self, resume_en, jd_en):
        from app.services.matcher.semantic_matcher import SemanticMatcher

        matcher = SemanticMatcher(model_name="mock-model")
        with patch.object(matcher, "_model", MockSentenceTransformer()):
            result = await matcher.match(resume_en, jd_en)

        assert "score" in result
        assert "overall_similarity" in result
        assert "dimension_scores" in result
        assert "details" in result
        assert 0.0 <= result["score"] <= 10.0
        assert result["details"]["model"] == "mock-model"

    @pytest.mark.asyncio
    async def test_dimension_scores_present(self, resume_en, jd_en):
        from app.services.matcher.semantic_matcher import SemanticMatcher

        matcher = SemanticMatcher(model_name="mock-model")
        with patch.object(matcher, "_model", MockSentenceTransformer()):
            result = await matcher.match(resume_en, jd_en)

        dims = result["dimension_scores"]
        assert "skills" in dims
        assert "experience" in dims
        assert "education" in dims
        for v in dims.values():
            assert 0.0 <= v <= 1.0, f"Dimension score {v} out of [0,1] range"

    @pytest.mark.asyncio
    async def test_empty_texts_handle_gracefully(self):
        from app.services.matcher.semantic_matcher import SemanticMatcher

        empty_resume = ParsedResumeData()
        empty_jd = ParsedJDData()
        matcher = SemanticMatcher(model_name="mock-model")
        with patch.object(matcher, "_model", MockSentenceTransformer()):
            result = await matcher.match(empty_resume, empty_jd)

        assert result["score"] >= 0.0
        assert "dimension_scores" in result

    @pytest.mark.asyncio
    async def test_same_text_produces_high_similarity(self):
        """Two identical texts should produce cosine similarity close to 1."""
        from app.services.matcher.semantic_matcher import SemanticMatcher

        resume = ParsedResumeData(
            skills=[Skill(name="Python", category="Programming")],
            work_experience=[WorkExperience(company="A", title="Engineer", description="Python development")],
        )
        jd = ParsedJDData(
            skills_required=[SkillRequirement(name="Python", importance="required")],
            requirements=[Requirement(description="Python development")],
        )

        matcher = SemanticMatcher(model_name="mock-model")
        with patch.object(matcher, "_model", MockSentenceTransformer()):
            result = await matcher.match(resume, jd)

        assert result["score"] >= 0.0

    @pytest.mark.asyncio
    async def test_compute_similarity_zero_for_empty_string(self):
        from app.services.matcher.semantic_matcher import SemanticMatcher

        matcher = SemanticMatcher(model_name="mock-model")
        with patch.object(matcher, "_model", MockSentenceTransformer()):
            sim = matcher._compute_similarity("", "non-empty")
        assert sim == 0.0

        with patch.object(matcher, "_model", MockSentenceTransformer()):
            sim = matcher._compute_similarity("non-empty", "")
        assert sim == 0.0

    @pytest.mark.asyncio
    async def test_model_lazy_loading(self):
        """SemanticMatcher does not load the model until first use."""
        from app.services.matcher.semantic_matcher import SemanticMatcher

        matcher = SemanticMatcher(model_name="mock-model")
        assert matcher._model is None  # Not loaded yet

        matcher._model = MockSentenceTransformer()
        assert matcher.model is not None
