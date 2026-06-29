"""
Stage 3: Semantic matching using BGE sentence embeddings.
Computes deep semantic similarity between resume and job description.
"""

import structlog
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.config import get_settings
from app.schemas.job import ParsedJDData
from app.schemas.resume import ParsedResumeData

logger = structlog.get_logger(__name__)


class SemanticMatcher:
    """BERT-based semantic matching using Chinese-optimized embeddings."""

    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.device = settings.EMBEDDING_DEVICE
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        """Lazy-load the embedding model."""
        if self._model is None:
            logger.info("Loading embedding model", model=self.model_name, device=self.device)
            self._model = SentenceTransformer(
                self.model_name,
                device=self.device,
            )
        return self._model

    async def match(self, resume: ParsedResumeData, jd: ParsedJDData) -> dict:
        """
        Returns:
            {
                "score": float (0-10),
                "overall_similarity": float (0-1),
                "dimension_scores": {
                    "skills": float,
                    "experience": float,
                    "education": float,
                },
                "details": dict
            }
        """
        # Build dimension-specific texts
        resume_texts = self._build_dimension_texts(resume)
        jd_texts = self._build_dimension_texts(jd)

        # Compute embeddings and similarities
        dimension_scores = {}

        # Overall similarity
        resume_overall = self._build_overall_text(resume)
        jd_overall = self._build_overall_text(jd)
        overall_sim = self._compute_similarity(resume_overall, jd_overall)

        # Per-dimension similarity
        for dim in ["skills", "experience", "education"]:
            if resume_texts.get(dim) and jd_texts.get(dim):
                dim_sim = self._compute_similarity(resume_texts[dim], jd_texts[dim])
            else:
                dim_sim = overall_sim
            dimension_scores[dim] = round(dim_sim, 4)

        score = overall_sim * 10

        return {
            "score": round(score, 2),
            "overall_similarity": round(overall_sim, 4),
            "dimension_scores": dimension_scores,
            "details": {
                "model": self.model_name,
                "device": self.device,
            },
        }

    def _compute_similarity(self, text1: str, text2: str) -> float:
        """Compute cosine similarity between two text embeddings."""
        if not text1.strip() or not text2.strip():
            return 0.0

        try:
            embeddings = self.model.encode(
                [text1, text2],
                show_progress_bar=False,
            )
            sim = cosine_similarity([embeddings[0]], [embeddings[1]])
            return float(sim[0][0])
        except Exception as e:
            logger.warning("Semantic similarity computation failed", error=str(e))
            return 0.0

    def _build_dimension_texts(self, data: ParsedResumeData | ParsedJDData) -> dict[str, str]:
        """Build text for each matching dimension."""
        texts = {}

        # Skills dimension
        if isinstance(data, ParsedResumeData):
            skills = [s.name for s in data.skills]
            texts["skills"] = " ".join(skills)

            exp_parts = []
            for exp in data.work_experience:
                exp_parts.append(f"{exp.title} {exp.company} {exp.description}")
            texts["experience"] = " ".join(exp_parts)

            edu_parts = []
            for edu in data.education:
                edu_parts.append(f"{edu.school} {edu.major} {edu.degree}")
            texts["education"] = " ".join(edu_parts)
        else:
            # JD data
            texts["skills"] = " ".join(s.name for s in data.skills_required)

            texts["experience"] = " ".join(
                req.description for req in data.requirements
                if "经验" in req.description or "experience" in req.description.lower()
            )

            edu_text = data.education_required.min_degree or ""
            edu_text += " " + " ".join(data.education_required.preferred_majors)
            texts["education"] = edu_text

        return texts

    def _build_overall_text(self, data: ParsedResumeData | ParsedJDData) -> str:
        """Build a comprehensive text representation."""
        parts = []

        if isinstance(data, ParsedResumeData):
            if data.basic_info.name:
                parts.append(data.basic_info.name)
            for skill in data.skills:
                parts.append(skill.name)
            for exp in data.work_experience:
                parts.append(f"{exp.title} {exp.company} {exp.description}")
                parts.extend(exp.achievements)
            for edu in data.education:
                parts.append(f"{edu.school} {edu.major} {edu.degree}")
            for proj in data.projects:
                parts.append(proj.description)
                parts.extend(proj.tech_stack)
        else:
            parts.append(data.basic_info.get("title", ""))
            for req in data.requirements:
                parts.append(req.description)
            parts.extend(data.responsibilities)
            for skill_req in data.skills_required:
                parts.append(skill_req.name)

        return " ".join(parts)
