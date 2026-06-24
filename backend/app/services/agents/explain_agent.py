"""
Explanation Agent - synthesizes matching results into a comprehensive,
human-readable report with visualizable data.
"""

import structlog

from app.services.agents.state import MatchingState

logger = structlog.get_logger(__name__)


async def explain_agent(state: MatchingState) -> MatchingState:
    """
    Agent that generates the final matching report.
    Synthesizes all previous agent outputs into structured, visualizable data.
    """
    try:
        # If there's already a hard pass, no explanation needed
        rule_result = state.get("rule_result", {})
        if rule_result.get("is_hard_pass"):
            return state

        # Enrich reasoning with structured highlights
        llm_result = state.get("llm_result", {})
        tfidf_result = state.get("tfidf_result", {})

        # Merge matched skills from all stages
        all_matched = set(state.get("matched_skills", []))
        if tfidf_result.get("matched_skills"):
            for m in tfidf_result["matched_skills"]:
                if isinstance(m, dict):
                    all_matched.add(m.get("jd_skill", ""))
                else:
                    all_matched.add(str(m))
        state["matched_skills"] = list(all_matched)

        # Generate structured report sections
        report = {
            "summary": _build_summary(state),
            "dimensions": _build_dimension_detail(state),
            "skill_gap": _build_skill_gap(state),
            "suggestions": state.get("suggestions", []),
            "ats_tips": _generate_ats_tips(state),
        }

        # Store report in state for API to retrieve
        state["reasoning"] = report["summary"] + "\n\n" + state.get("reasoning", "")
        # Enrich suggestions with ATS tips if LLM suggestions are limited
        state["suggestions"] = report["suggestions"]

        logger.info("Explanation report generated")

    except Exception as e:
        logger.error("Explanation generation failed", error=str(e))
        # Non-fatal: matching results are still valid

    return state


def _build_summary(state: MatchingState) -> str:
    """Build executive summary."""
    score = state.get("overall_score", 0)
    resume = state.get("resume_parsed")
    jd = state.get("jd_parsed")

    candidate_name = resume.basic_info.name if resume else "候选人"
    job_title = jd.basic_info.get("title", "该岗位") if jd else "该岗位"

    if score >= 8:
        level = "非常匹配"
    elif score >= 6:
        level = "比较匹配"
    elif score >= 4:
        level = "部分匹配"
    else:
        level = "匹配度较低"

    return f"{candidate_name} 与 {job_title} 的综合匹配度为 {score}/10，{level}。"


def _build_dimension_detail(state: MatchingState) -> dict:
    """Build dimensional analysis detail."""
    dims = state.get("dimension_scores")
    if not dims:
        return {}

    return {
        "education": {
            "score": dims.education,
            "label": "学历匹配",
            "max": 10,
        },
        "skills": {
            "score": dims.skills,
            "label": "技能匹配",
            "max": 10,
        },
        "experience": {
            "score": dims.experience,
            "label": "经验匹配",
            "max": 10,
        },
        "certifications": {
            "score": dims.certifications,
            "label": "证书匹配",
            "max": 10,
        },
        "languages": {
            "score": dims.languages,
            "label": "语言能力",
            "max": 10,
        },
        "location": {
            "score": dims.location,
            "label": "地点匹配",
            "max": 10,
        },
        "overall": {
            "score": dims.overall,
            "label": "综合得分",
            "max": 10,
        },
    }


def _build_skill_gap(state: MatchingState) -> dict:
    """Build skill gap analysis data."""
    return {
        "matched": state.get("matched_skills", []),
        "missing": state.get("missing_skills", []),
    }


def _generate_ats_tips(state: MatchingState) -> list[str]:
    """Generate ATS optimization tips personalized to resume type."""
    resume = state.get("resume_parsed")
    is_campus = resume.resume_type == "campus" if resume else False

    # Common tips for all resume types
    common_tips = [
        "确保简历包含目标岗位的关键词，关键词密度建议 3-5%",
        '使用标准的章节标题(如 [工作经历] [教育背景] [专业技能])，便于 ATS 解析',
        "避免使用图片、表格、特殊符号，这些可能无法被 ATS 正确解析",
        "文件格式推荐使用 PDF，确保跨平台兼容性",
    ]

    # Campus-specific tips
    campus_tips = [
        "校招简历建议将 GPA（如 ≥3.5）和排名突出展示，这是 HR 筛选的重要指标",
        "如有多段实习经历，按时间倒序排列，每段突出 2-3 个量化成果",
        "项目经历和课程设计是评估技术能力的重要依据，建议用 STAR 法则描述",
        "竞赛获奖、奖学金等荣誉建议单独列出，展示综合素质",
        "预计毕业时间务必清晰标注，避免 HR 因信息缺失而过滤",
        "技术栈按熟练程度排序，最擅长的排在最前面",
    ]

    # Experienced-specific tips
    experienced_tips = [
        "工作经历描述中尽量包含可量化的成果(如 [提升系统性能 30%]、[带领 5 人团队])",
        "每段工作经历建议用 STAR 法则展开：情境→任务→行动→结果",
        "管理经验、团队规模、预算掌控等软技能重点突出",
        "技术栈按精通程度分类展示，区分 [精通] [熟练] [了解]",
        "5 年以上的早期工作经历可简略描述，重点放在最近 3-5 年",
        "如有技术博客、开源贡献、技术演讲等社区影响力，可加分展示",
    ]

    # Note: when LLM is enabled, LLM-generated suggestions take precedence.
    # These tips serve as a baseline when LLM suggestions are limited.
    llm_suggestions = state.get("suggestions", [])
    if len(llm_suggestions) >= 4:
        # LLM already gave good suggestions, just add 1-2 ATS tips as supplement
        return llm_suggestions

    # Merge: LLM suggestions first, then ATS tips to fill up to ~6 items
    tips = list(llm_suggestions)
    type_tips = campus_tips if is_campus else experienced_tips
    for tip in type_tips + common_tips:
        if len(tips) >= 6:
            break
        if tip not in tips:
            tips.append(tip)
    return tips
