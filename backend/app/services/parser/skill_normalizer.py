"""
Skill name normalization and taxonomy mapping.
Maps variant skill names (e.g., "React.js", "ReactJS") to canonical forms.
"""

import json
import os

import structlog
from fuzzywuzzy import fuzz

logger = structlog.get_logger(__name__)

# Built-in skill taxonomy
DEFAULT_SKILL_TAXONOMY = {
    "categories": {
        "programming_languages": {
            "display": "编程语言",
            "skills": {
                "Python": ["python", "python3", "py"],
                "Java": ["java", "j2ee", "java se", "java ee"],
                "JavaScript": ["javascript", "js", "es6", "es2015", "node.js开发"],
                "TypeScript": ["typescript", "ts"],
                "Go": ["go", "golang"],
                "Rust": ["rust", "rust-lang"],
                "C++": ["c++", "cpp", "c plus plus"],
                "C": ["c语言", "c programming"],
                "C#": ["c#", "csharp", "c sharp"],
                "PHP": ["php"],
                "Ruby": ["ruby"],
                "Swift": ["swift"],
                "Kotlin": ["kotlin"],
                "Scala": ["scala"],
                "R": ["r语言", "r programming"],
                "SQL": ["sql", "mysql语法", "postgresql语法", "t-sql"],
                "HTML": ["html", "html5"],
                "CSS": ["css", "css3"],
                "Shell": ["shell", "bash", "zsh"],
            },
        },
        "frameworks": {
            "display": "框架与库",
            "skills": {
                "React": ["react", "react.js", "reactjs", "react native"],
                "Vue": ["vue", "vue.js", "vuejs", "vue3"],
                "Angular": ["angular", "angularjs", "angular2+"],
                "Next.js": ["next.js", "nextjs", "next"],
                "Django": ["django", "django rest framework", "drf"],
                "Flask": ["flask"],
                "FastAPI": ["fastapi"],
                "Spring Boot": ["spring boot", "springboot", "spring"],
                "Express": ["express", "express.js", "expressjs"],
                "PyTorch": ["pytorch", "torch"],
                "TensorFlow": ["tensorflow", "tf"],
                "LangChain": ["langchain"],
                "LangGraph": ["langgraph"],
                "LlamaIndex": ["llamaindex", "llama_index", "llama index"],
                "Transformers": ["transformers", "huggingface transformers", "hugging face"],
                "Pandas": ["pandas"],
                "NumPy": ["numpy", "np"],
                "Scikit-learn": ["scikit-learn", "scikit learn", "sklearn"],
                "jQuery": ["jquery"],
                "Bootstrap": ["bootstrap"],
                "Tailwind CSS": ["tailwind", "tailwindcss", "tailwind css"],
            },
        },
        "databases": {
            "display": "数据库",
            "skills": {
                "MySQL": ["mysql"],
                "PostgreSQL": ["postgresql", "postgres", "pg"],
                "MongoDB": ["mongodb", "mongo"],
                "Redis": ["redis"],
                "Elasticsearch": ["elasticsearch", "es"],
                "SQLite": ["sqlite"],
                "Oracle": ["oracle", "oracle db"],
                "SQL Server": ["sql server", "mssql", "sqlserver"],
            },
        },
        "cloud_devops": {
            "display": "云平台与DevOps",
            "skills": {
                "Docker": ["docker", "docker compose", "docker-compose"],
                "Kubernetes": ["kubernetes", "k8s"],
                "AWS": ["aws", "amazon web services", "amazon云"],
                "Azure": ["azure", "微软云"],
                "GCP": ["gcp", "google cloud", "google云"],
                "Linux": ["linux", "ubuntu", "centos", "debian"],
                "Git": ["git", "git版本控制"],
                "Nginx": ["nginx"],
                "Jenkins": ["jenkins"],
                "GitHub Actions": ["github actions", "github action"],
                "CI/CD": ["ci/cd", "cicd", "持续集成", "持续部署"],
                "Kafka": ["kafka", "apache kafka"],
                "RabbitMQ": ["rabbitmq"],
            },
        },
        "ai_ml": {
            "display": "AI/机器学习",
            "skills": {
                "深度学习": ["深度学习", "deep learning"],
                "机器学习": ["机器学习", "machine learning", "ml"],
                "自然语言处理": ["自然语言处理", "nlp", "自然语言理解", "nlu"],
                "计算机视觉": ["计算机视觉", "cv", "computer vision"],
                "大语言模型": ["大语言模型", "llm", "large language model", "大模型"],
                "RAG": ["rag", "检索增强生成"],
                "Agent": ["ai agent", "智能体", "agent开发"],
            },
        },
        "soft_skills": {
            "display": "软技能",
            "skills": {
                "团队管理": ["团队管理", "团队领导", "team management"],
                "项目管理": ["项目管理", "project management"],
                "沟通能力": ["沟通能力", "沟通协调"],
                "英语": ["英语", "english"],
            },
        },
    }
}


class SkillNormalizer:
    """Normalize skill names to a unified taxonomy."""

    def __init__(self, taxonomy_path: str | None = None):
        self.taxonomy = self._load_taxonomy(taxonomy_path)
        # Build alias → (canonical_name, category) lookup
        self._alias_map: dict[str, tuple[str, str]] = {}
        self._build_alias_map()

    def _load_taxonomy(self, path: str | None) -> dict:
        """Load skill taxonomy from file or use default."""
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return DEFAULT_SKILL_TAXONOMY

    def _build_alias_map(self):
        """Build a lookup from all aliases to canonical names."""
        for cat_key, cat_data in self.taxonomy.get("categories", {}).items():
            for canonical, aliases in cat_data.get("skills", {}).items():
                self._alias_map[canonical.lower()] = (canonical, cat_key)
                for alias in aliases:
                    self._alias_map[alias.lower()] = (canonical, cat_key)

    def normalize(self, skill_name: str) -> tuple[str, str, str | None]:
        """Normalize a skill name.

        Args:
            skill_name: Raw skill name from resume.

        Returns:
            Tuple of (canonical_name, category_key, category_display) or
            (original_name, "other", "其他") if no match found.
        """
        name_lower = skill_name.lower().strip()

        # 1. Exact match
        if name_lower in self._alias_map:
            canonical, cat_key = self._alias_map[name_lower]
            cat_display = self.taxonomy["categories"][cat_key]["display"]
            return canonical, cat_key, cat_display

        # 2. Fuzzy match (token set ratio)
        best_score = 0
        best_match = None
        for alias, (canonical, cat_key) in self._alias_map.items():
            score = fuzz.token_set_ratio(name_lower, alias)
            if score > best_score and score >= 85:
                best_score = score
                best_match = (canonical, cat_key)

        if best_match:
            canonical, cat_key = best_match
            cat_display = self.taxonomy["categories"][cat_key]["display"]
            return canonical, cat_key, cat_display

        # 3. No match
        return skill_name, "other", "其他"

    def normalize_list(self, skills: list[str]) -> list[dict]:
        """Normalize a list of skill names and return structured data.

        Returns:
            List of dicts with keys: name, category, category_display
        """
        normalized = []
        seen = set()

        for skill in skills:
            canonical, cat_key, cat_display = self.normalize(skill)
            if canonical.lower() not in seen:
                seen.add(canonical.lower())
                normalized.append({
                    "name": canonical,
                    "category": cat_key,
                    "category_display": cat_display,
                })
        return normalized

    def get_all_canonical_skills(self) -> list[str]:
        """Get the list of all canonical skill names in the taxonomy."""
        return list(set(v[0] for v in self._alias_map.values()))
