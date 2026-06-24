"""
Language detector for resume text.
Detects whether text is primarily Chinese, English, or mixed.
Used to select appropriate spaCy model and regex patterns.
"""

import re


def detect_language(text: str) -> str:
    """
    Detect the primary language of the resume text.

    Returns:
        'zh' — primarily Chinese
        'en' — primarily English
        'mixed' — significant amounts of both
    """
    if not text or not text.strip():
        return "zh"  # Default to Chinese

    # Count CJK characters (Chinese, Japanese, Korean)
    cjk_pattern = re.compile(r"[一-鿿㐀-䶿豈-﫿]")
    cjk_count = len(cjk_pattern.findall(text))

    # Count Latin alphabet characters
    latin_pattern = re.compile(r"[a-zA-Z]")
    latin_count = len(latin_pattern.findall(text))

    total = cjk_count + latin_count
    if total == 0:
        return "zh"  # Default

    cjk_ratio = cjk_count / total

    if cjk_ratio >= 0.60:
        return "zh"
    elif cjk_ratio <= 0.15:
        return "en"
    else:
        return "mixed"


def get_spacy_model(language: str) -> str:
    """
    Return the appropriate spaCy model name for the detected language.

    Args:
        language: 'zh', 'en', or 'mixed'

    Returns:
        spaCy model name string
    """
    models = {
        "zh": "zh_core_web_sm",
        "en": "en_core_web_sm",
        "mixed": "zh_core_web_sm",  # Default to Chinese for mixed
    }
    return models.get(language, "zh_core_web_sm")
