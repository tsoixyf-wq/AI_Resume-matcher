"""Tests for the resume parsing engine."""

import pytest
from app.services.parser.document_loader import DocumentLoader
from app.services.parser.ner_extractor import NERExtractor
from app.services.parser.skill_normalizer import SkillNormalizer


SAMPLE_RESUME_TEXT = """
张三
邮箱: zhangsan@example.com
电话: 13800138000
城市: 北京

教育背景
北京大学 | 计算机科学与技术 | 硕士

专业技能
Python, FastAPI, Docker, PostgreSQL, Redis, PyTorch, LangChain

工作经历
字节跳动 | 后端开发工程师 | 2023.07 - 至今
负责微服务架构设计与开发
"""


class TestDocumentLoader:
    """Test document loading."""

    @pytest.mark.asyncio
    async def test_load_txt(self, tmp_path):
        """Test loading a text file."""
        file_path = tmp_path / "test_resume.txt"
        file_path.write_text(SAMPLE_RESUME_TEXT, encoding="utf-8")

        text = await DocumentLoader.load(str(file_path))
        assert "张三" in text
        assert "zhangsan@example.com" in text


class TestNERExtractor:
    """Test NER extraction."""

    @pytest.mark.asyncio
    async def test_extract_email(self):
        """Test email extraction."""
        extractor = NERExtractor()
        email = extractor._extract_email(SAMPLE_RESUME_TEXT)
        assert email == "zhangsan@example.com"

    @pytest.mark.asyncio
    async def test_extract_phone(self):
        """Test phone extraction."""
        extractor = NERExtractor()
        phone = extractor._extract_phone(SAMPLE_RESUME_TEXT)
        assert phone == "13800138000"

    @pytest.mark.asyncio
    async def test_extract_skills(self):
        """Test skill extraction from known vocabulary."""
        extractor = NERExtractor()
        skills = extractor._extract_skills(SAMPLE_RESUME_TEXT)
        assert "Python" in skills
        assert "FastAPI" in skills
        assert "Docker" in skills
        assert "PostgreSQL" in skills
        assert "Redis" in skills

    @pytest.mark.asyncio
    async def test_extract_full(self):
        """Test full extraction pipeline."""
        extractor = NERExtractor()
        result = await extractor.extract(SAMPLE_RESUME_TEXT)
        assert result["email"] == "zhangsan@example.com"
        assert result["phone"] == "13800138000"
        assert len(result["skills"]) > 0


class TestSkillNormalizer:
    """Test skill normalization."""

    def test_normalize_exact_match(self):
        """Test exact match normalization."""
        normalizer = SkillNormalizer()
        canonical, cat_key, cat_display = normalizer.normalize("Python")
        assert canonical == "Python"
        assert cat_key == "programming_languages"

    def test_normalize_alias(self):
        """Test alias-based normalization."""
        normalizer = SkillNormalizer()
        canonical, cat_key, cat_display = normalizer.normalize("react.js")
        assert canonical == "React"
        assert cat_key == "frameworks"

    def test_normalize_fuzzy(self):
        """Test fuzzy match normalization."""
        normalizer = SkillNormalizer()
        canonical, cat_key, cat_display = normalizer.normalize("PostgreSQL数据库")
        # Should fuzzy match to PostgreSQL
        assert "PostgreSQL" in canonical or cat_key != "other"

    def test_normalize_unknown(self):
        """Test unknown skill falls back to original."""
        normalizer = SkillNormalizer()
        canonical, cat_key, cat_display = normalizer.normalize("XYZRandomSkill")
        assert canonical == "XYZRandomSkill"
        assert cat_key == "other"

    def test_normalize_list_dedup(self):
        """Test list normalization with dedup."""
        normalizer = SkillNormalizer()
        result = normalizer.normalize_list(["Python", "python", "py", "Docker"])
        # Should deduplicate Python/python/py
        assert len(result) <= 3
        names = [r["name"] for r in result]
        assert "Python" in names
        assert "Docker" in names
