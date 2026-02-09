"""Application configuration."""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
SCREENSHOTS_DIR = UPLOADS_DIR / "screenshots"


class Settings:
    database_url: str = f"sqlite:///{BASE_DIR / 'app.db'}"
    uploads_dir: Path = UPLOADS_DIR
    screenshots_dir: Path = SCREENSHOTS_DIR
    max_upload_mb: int = 10
    allowed_image_extensions: set = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp"})


settings = Settings()

# Ensure directories exist
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
