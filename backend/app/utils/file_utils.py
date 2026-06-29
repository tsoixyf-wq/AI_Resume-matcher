"""File handling utilities for resume parsing."""

import hashlib
import os
import uuid

from app.core.config import get_settings

settings = get_settings()

ALLOWED_EXTENSIONS = settings.ALLOWED_EXTENSIONS
MAX_UPLOAD_SIZE = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


def validate_file(filename: str, file_size: int) -> tuple[bool, str]:
    """Validate uploaded file extension and size.

    Returns:
        (is_valid, error_message)
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"不支持的文件格式: .{ext}，支持的格式: {', '.join(ALLOWED_EXTENSIONS)}"

    if file_size > MAX_UPLOAD_SIZE:
        return False, f"文件大小超过限制 ({settings.MAX_UPLOAD_SIZE_MB}MB)"

    return True, ""


def generate_file_path(original_filename: str, upload_dir: str | None = None) -> str:
    """Generate a unique file path for storing an uploaded resume.

    Format: {upload_dir}/{uuid}_{sanitized_filename}
    """
    upload_dir = upload_dir or str(settings.DATA_DIR / "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else "txt"
    safe_name = f"{uuid.uuid4().hex[:12]}.{ext}"
    return os.path.join(upload_dir, safe_name)


def compute_file_hash(file_path: str) -> str:
    """Compute SHA-256 hash of a file for deduplication."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()
