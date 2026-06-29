"""Tests for the LangGraph agent pipeline — graph structure and node logic."""

from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.job import (
    EducationRequirement,
    ParsedJDData,
    SkillRequirement,
)
from app.schemas.matching import DimensionScores
from app.schemas.resume import (
    BasicInfo,
    Education,
    ParsedResumeData,
    Skill,
    WorkExperience,
)
from app.services.agents.graph import check_error, handle_error_node
from app.services.agents.state import MatchingState


@pytest.fixture
def base_state():
    """Minimal valid MatchingState."""
    return MatchingState(
        resume_text="",
        jd_text="",
        enable_llm=False,
        resume_parsed=None,
        jd_parsed=None,
        rule_result=None,
        tfidf_result=None,
        semantic_result=None,
        llm_result=None,
        overall_score=0.0,
        dimension_scores=None,
        matched_skills=[],
        missing_skills=[],
        reasoning="",
        suggestions=[],
        is_hard_pass=False,
        error=None,
    )


@pytest.fixture
def parsed_resume():
    return ParsedResumeData(
        basic_info=BasicInfo(name="Test", email="test@test.com", years_of_experience=3),
        skills=[Skill(name="Python", category="Programming")],
        education=[Education(school="Test U", degree="Bachelor", major="CS")],
        work_experience=[WorkExperience(company="Corp", title="Engineer", description="Dev")],
        resume_type="experienced",
    )


@pytest.fixture
def parsed_jd():
    return ParsedJDData(
        basic_info={"title": "Software Engineer"},
        skills_required=[SkillRequirement(name="Python", importance="required")],
        education_required=EducationRequirement(min_degree="Bachelor"),
    )


class TestCheckError:
    """Tests for the conditional edge router."""

    def test_no_error_returns_continue(self, base_state):
        assert check_error(base_state) == "continue"

    def test_with_error_returns_error(self, base_state):
        state = base_state.copy()
        state["error"] = "Something went wrong"
        assert check_error(state) == "error"

    def test_empty_string_error_counts_as_falsy(self, base_state):
        state = base_state.copy()
        state["error"] = ""
        # empty string is falsy → "continue"
        assert check_error(state) == "continue"


class TestHandleErrorNode:
    """Tests for the error handling node."""

    def test_sets_overall_score_to_zero(self, base_state):
        state = base_state.copy()
        state["error"] = "Parsing failed"
        result = handle_error_node(state)
        assert result["overall_score"] == 0.0

    def test_sets_reasoning_with_error_message(self, base_state):
        state = base_state.copy()
        state["error"] = "Resume parse timeout"
        result = handle_error_node(state)
        assert "Resume parse timeout" in result["reasoning"]
        assert "处理出错" in result["reasoning"]

    def test_handles_none_error_gracefully(self, base_state):
        state = base_state.copy()
        state["error"] = None
        result = handle_error_node(state)
        # When error key exists but is None, the f-string renders "处理出错: None"
        assert "处理出错" in result["reasoning"]


class TestParseAllAgent:
    """Tests for parse_all_agent (pre-parsed shortcut)."""

    @pytest.mark.asyncio
    async def test_skips_when_pre_parsed_data_present(self, base_state, parsed_resume, parsed_jd):
        from app.services.agents.graph import parse_all_agent

        state = base_state.copy()
        state["resume_parsed"] = parsed_resume
        state["jd_parsed"] = parsed_jd

        result = await parse_all_agent(state)
        # Should return the same state unchanged (shortcut path)
        assert result["resume_parsed"] is parsed_resume
        assert result["jd_parsed"] is parsed_jd
        assert result.get("error") is None

    @pytest.mark.asyncio
    async def test_runs_parse_when_no_pre_parsed_data(self, base_state):
        from app.services.agents.graph import parse_all_agent

        state = base_state.copy()
        state["resume_text"] = "张三\nPython工程师\n3年经验"
        state["jd_text"] = "Python工程师\n要求3年经验"

        result = await parse_all_agent(state)
        # Should have parsed data or an error
        has_parsed = (
            result.get("resume_parsed") is not None
            and result.get("jd_parsed") is not None
        )
        has_error = result.get("error") is not None
        assert has_parsed or has_error, (
            f"Expected either parsed data or error, got neither. "
            f"resume_parsed={result.get('resume_parsed')}, jd_parsed={result.get('jd_parsed')}"
        )


def _mock_matchers():
    """Patch all matchers to return fast deterministic results (no ML models)."""
    return (
        patch(
            "app.services.agents.match_agent.RuleMatcher.match",
            new_callable=AsyncMock,
            return_value={
                "score": 7.0,
                "is_hard_pass": False,
                "hard_pass_reasons": [],
                "details": {
                    "degree": {"passed": True, "actual": "硕士", "required": "本科"},
                    "experience": {"passed": True},
                    "skills": {"passed": True, "matched": ["Python"], "missing": []},
                },
            },
        ),
        patch(
            "app.services.agents.match_agent.TFIDFMatcher.match",
            new_callable=AsyncMock,
            return_value={"score": 6.5, "details": {}},
        ),
        patch(
            "app.services.agents.match_agent.SemanticMatcher.match",
            new_callable=AsyncMock,
            return_value={
                "score": 6.8,
                "overall_similarity": 0.68,
                "dimension_scores": {"skills": 0.7, "experience": 0.65, "education": 0.69},
                "details": {},
            },
        ),
    )


class TestMatchAgent:
    """Tests for match_agent node — all matchers mocked to avoid ML model loading."""

    @pytest.mark.asyncio
    async def test_error_when_no_parsed_data(self, base_state):
        from app.services.agents.match_agent import match_agent

        state = base_state.copy()
        result = await match_agent(state)
        assert result.get("error") is not None
        assert "为空" in result["error"]

    @pytest.mark.asyncio
    async def test_matches_with_parsed_data_no_llm(self, base_state, parsed_resume, parsed_jd):
        from app.services.agents.match_agent import match_agent

        mocks = _mock_matchers()
        state = base_state.copy()
        state["resume_parsed"] = parsed_resume
        state["jd_parsed"] = parsed_jd
        state["enable_llm"] = False

        with mocks[0] as mock_rule, mocks[1] as mock_tfidf, mocks[2] as mock_semantic:
            result = await match_agent(state)

        assert result.get("error") is None, f"Unexpected error: {result.get('error')}"
        assert result.get("overall_score", -1) >= 0
        assert result.get("rule_result") is not None
        assert result.get("tfidf_result") is not None
        assert result.get("semantic_result") is not None
        assert result.get("llm_result") is None
        mock_rule.assert_called_once()
        mock_tfidf.assert_called_once()
        mock_semantic.assert_called_once()

    @pytest.mark.asyncio
    async def test_hard_pass_short_circuits(self, base_state):
        from app.services.agents.match_agent import match_agent

        resume = ParsedResumeData(
            basic_info=BasicInfo(name="Noob", years_of_experience=0),
            resume_type="experienced",
        )

        # Mock RuleMatcher to return a hard pass
        with patch(
            "app.services.agents.match_agent.RuleMatcher.match",
            new_callable=AsyncMock,
            return_value={
                "score": 0.0,
                "is_hard_pass": True,
                "hard_pass_reasons": ["不满足最低学历要求"],
                "details": {
                    "degree": {"passed": False, "actual": "无", "required": "本科"},
                    "skills": {"passed": False, "matched": [], "missing": ["Python"]},
                },
            },
        ) as mock_rule:
            state = base_state.copy()
            state["resume_parsed"] = resume
            state["jd_parsed"] = ParsedJDData(
                basic_info={"title": "Senior Dev"},
                skills_required=[SkillRequirement(name="Python", importance="required")],
                education_required=EducationRequirement(min_degree="本科"),
            )
            state["enable_llm"] = False

            result = await match_agent(state)

        assert result["is_hard_pass"] is True
        assert result["overall_score"] == 0.0
        assert result.get("error") is None
        mock_rule.assert_called_once()
        # TF-IDF and Semantic should NOT have been called (short-circuited)
        assert result.get("tfidf_result") is None
