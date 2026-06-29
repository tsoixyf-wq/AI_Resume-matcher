"""
Stage 1: Rule-based hard-filter matching.
Checks mandatory requirements: degree, years of experience, must-have skills.
If any hard requirement fails, the candidate is filtered out (hard pass).
"""

import structlog

from app.core.config import get_settings
from app.schemas.job import ParsedJDData
from app.schemas.resume import ParsedResumeData

logger = structlog.get_logger(__name__)

# Degree hierarchy for comparison
DEGREE_RANK = {
    "高中": 1, "中专": 2, "大专": 3,
    "本科": 4, "学士": 4, "bachelor": 4,
    "硕士": 5, "研究生": 5, "master": 5, "mba": 5,
    "博士": 6, "doctorate": 6, "phd": 6, "ph.d": 6,
}


class RuleMatcher:
    """Check hard requirements — if any fail, the candidate gets a hard pass."""

    async def match(
        self,
        resume: ParsedResumeData,
        jd: ParsedJDData,
    ) -> dict:
        """
        Returns:
            {
                "score": float (0-10),
                "is_hard_pass": bool,
                "hard_pass_reasons": list[str],
                "details": dict
            }
        """
        reasons = []
        details = {}

        # 1. Check minimum degree
        degree_check = self._check_degree(resume, jd)
        details["degree"] = degree_check
        if not degree_check["passed"]:
            reasons.append(degree_check["reason"])

        # 2. Check minimum years of experience
        # Campus/fresh-grad resumes skip the min_years hard check
        is_campus = resume.resume_type == "campus"
        if is_campus:
            details["experience"] = {
                "passed": True,
                "reason": "校招简历，不检查工作年限",
                "required": None,
                "actual": None,
                "skipped": True,
            }
        else:
            exp_check = self._check_experience(resume, jd)
            details["experience"] = exp_check
            if not exp_check["passed"]:
                reasons.append(exp_check["reason"])

        # 3. Check must-have skills
        skill_check = self._check_must_skills(resume, jd)
        details["skills"] = skill_check
        if not skill_check["passed"]:
            reasons.append(skill_check["reason"])

        # 4. Check location
        details["location"] = self._check_location(resume, jd)

        # 5. Check certifications
        details["certifications"] = self._check_certifications(resume, jd)

        # 6. Campus-specific checks (bonus evaluation, not hard-pass)
        if is_campus:
            details["gpa"] = self._check_gpa(resume, jd)
            details["internships"] = self._check_internships(resume)

        is_hard_pass = len(reasons) > 0
        score = 0.0 if is_hard_pass else self._calculate_rule_score(details)

        return {
            "score": score,
            "is_hard_pass": is_hard_pass,
            "hard_pass_reasons": reasons,
            "details": details,
        }

    def _check_degree(self, resume: ParsedResumeData, jd: ParsedJDData) -> dict:
        """Check if the candidate's highest degree meets the requirement."""
        min_degree = jd.education_required.min_degree
        if not min_degree:
            return {"passed": True, "reason": "", "required": None, "actual": None}

        min_rank = self._get_degree_rank(min_degree)
        if min_rank == 0:
            return {"passed": True, "reason": "", "required": min_degree, "actual": "unknown"}

        # Find candidate's highest degree
        highest_rank = 0
        highest_degree = ""
        for edu in resume.education:
            rank = self._get_degree_rank(edu.degree)
            if rank > highest_rank:
                highest_rank = rank
                highest_degree = edu.degree

        if highest_rank < min_rank:
            return {
                "passed": False,
                "reason": f"学历不满足：要求{min_degree}及以上，实际{highest_degree or '未知'}",
                "required": min_degree,
                "actual": highest_degree or "未知",
            }

        return {
            "passed": True,
            "reason": "",
            "required": min_degree,
            "actual": highest_degree,
        }

    def _check_experience(self, resume: ParsedResumeData, jd: ParsedJDData) -> dict:
        """Check if the candidate has enough work experience."""
        min_years = jd.experience_required.min_years
        if not min_years:
            return {"passed": True, "reason": "", "required": None, "actual": None}

        candidate_years = resume.basic_info.years_of_experience or 0

        if candidate_years < min_years:
            return {
                "passed": False,
                "reason": f"工作年限不满足：要求{min_years}年以上，实际{candidate_years}年",
                "required": min_years,
                "actual": candidate_years,
            }

        return {
            "passed": True,
            "reason": "",
            "required": min_years,
            "actual": candidate_years,
        }

    def _check_must_skills(self, resume: ParsedResumeData, jd: ParsedJDData) -> dict:
        """Check if the candidate has all must-have skills."""
        must_skills = [
            s for s in jd.skills_required
            if s.importance == "required"
        ]
        if not must_skills:
            return {"passed": True, "reason": "", "required": [], "missing": []}

        candidate_skills_lower = {s.name.lower() for s in resume.skills}
        missing = []
        for skill in must_skills:
            # Use fuzzy containment
            found = False
            for cs in candidate_skills_lower:
                if skill.name.lower() in cs or cs in skill.name.lower():
                    found = True
                    break
            if not found:
                missing.append(skill.name)

        threshold = get_settings().MUST_SKILL_MISSING_THRESHOLD
        if len(missing) > len(must_skills) * threshold:  # Configurable: default 50%
            return {
                "passed": False,
                "reason": f"必备技能缺失过多：缺失 {missing}",
                "required": [s.name for s in must_skills],
                "missing": missing,
            }

        return {
            "passed": True,
            "reason": "",
            "required": [s.name for s in must_skills],
            "missing": missing,
        }

    def _check_gpa(self, resume: ParsedResumeData, jd: ParsedJDData) -> dict:
        """Check GPA for campus resumes (informational, not hard-pass)."""
        gpas = [
            edu.gpa
            for edu in resume.education
            if edu.gpa is not None
        ]
        if not gpas:
            return {"has_gpa": False, "gpa": None, "note": "简历未提供 GPA"}

        best_gpa = max(gpas)
        note = ""
        if best_gpa >= 3.5:
            note = "GPA 优秀"
        elif best_gpa >= 3.0:
            note = "GPA 良好"
        elif best_gpa >= 2.5:
            note = "GPA 一般"
        else:
            note = "GPA 偏低"

        return {"has_gpa": True, "gpa": best_gpa, "note": note}

    def _check_internships(self, resume: ParsedResumeData) -> dict:
        """Check internship experience for campus resumes."""
        internships = [
            w for w in resume.work_experience
            if w.employment_type == "internship"
        ]
        count = len(internships)
        companies = [i.company for i in internships if i.company]

        note = ""
        if count >= 3:
            note = "实习经历丰富"
        elif count >= 1:
            note = f"有 {count} 段实习经历"
        else:
            note = "无实习经历"

        return {
            "internship_count": count,
            "companies": companies,
            "note": note,
        }

    def _check_location(self, resume: ParsedResumeData, jd: ParsedJDData) -> dict:
        """Check location match between candidate and job (bonus, not hard-pass)."""
        jd_location = jd.basic_info.get("location", "")
        candidate_city = resume.basic_info.city

        if not jd_location or not candidate_city:
            return {
                "passed": True,
                "score": 5.0,
                "note": "无地点信息",
                "jd_location": jd_location or "未知",
                "candidate_location": candidate_city or "未知",
            }

        # Simple containment check
        jd_lower = jd_location.lower()
        city_lower = candidate_city.lower()
        if city_lower in jd_lower or jd_lower in city_lower:
            return {
                "passed": True,
                "score": 10.0,
                "note": "地点匹配",
                "jd_location": jd_location,
                "candidate_location": candidate_city,
            }

        return {
            "passed": True,
            "score": 3.0,
            "note": "异地求职",
            "jd_location": jd_location,
            "candidate_location": candidate_city,
        }

    def _check_certifications(self, resume: ParsedResumeData, jd: ParsedJDData) -> dict:
        """Check certifications match (bonus, not hard-pass)."""
        resume_certs = [c.name.lower() for c in resume.certifications]

        if not resume_certs:
            return {
                "passed": True,
                "score": 5.0,
                "note": "简历未提供证书信息",
                "matched": [],
                "total": 0,
            }

        # Look for cert-related keywords in JD requirements and responsibilities
        jd_text = " ".join(jd.responsibilities + [r.description for r in jd.requirements])
        jd_text_lower = jd_text.lower()

        cert_keywords = ["证书", "认证", "certification", "certificate", "license",
                         "aws certified", "cka", "ckad", "pmp", "cfa", "cpa",
                         "rhce", "ccie", "cissp", "acp", "csm"]

        jd_wants_certs = any(kw in jd_text_lower for kw in cert_keywords)

        if not jd_wants_certs:
            return {
                "passed": True,
                "score": 7.0,
                "note": "岗位未明确要求证书",
                "matched": [],
                "total": len(resume_certs),
            }

        # Simple keyword matching for cert names
        matched = [c.name for c in resume.certifications
                   if any(kw in c.name.lower() for kw in cert_keywords)]

        score = min(10.0, 5.0 + len(matched) * 2.5) if matched else 3.0
        return {
            "passed": True,
            "score": score,
            "note": f"匹配证书: {len(matched)}/{len(resume_certs)}",
            "matched": matched,
            "total": len(resume_certs),
        }

    def _calculate_rule_score(self, details: dict) -> float:
        """Calculate rule-based score (0-10) from check details."""
        scores = []

        # Degree: partial credit based on rank difference
        degree_detail = details.get("degree", {})
        if degree_detail.get("required"):
            req_rank = self._get_degree_rank(degree_detail["required"])
            actual_rank = self._get_degree_rank(degree_detail.get("actual", ""))
            if actual_rank >= req_rank:
                scores.append(10.0)
            else:
                scores.append(max(0, (actual_rank / req_rank) * 10))

        # Experience
        exp_detail = details.get("experience", {})
        if exp_detail.get("required"):
            required = exp_detail["required"]
            actual = exp_detail.get("actual", 0)
            if actual >= required:
                scores.append(10.0)
            else:
                scores.append(max(0, (actual / required) * 10))

        # Skills
        skill_detail = details.get("skills", {})
        if skill_detail.get("required"):
            missing = len(skill_detail.get("missing", []))
            total = len(skill_detail["required"])
            if total > 0:
                scores.append(((total - missing) / total) * 10)

        return sum(scores) / len(scores) if scores else 10.0

    @staticmethod
    def _get_degree_rank(degree: str) -> int:
        """Get numeric rank for a degree string."""
        degree_lower = degree.lower().strip()
        for key, rank in DEGREE_RANK.items():
            if key in degree_lower:
                return rank
        return 0  # Unknown
