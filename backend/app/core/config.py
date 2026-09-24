"""
System configuration and environment management.
Supports multi-profile execution: FAST, BALANCED, and DEEP_FORENSIC.
"""

from pathlib import Path
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application Metadata
    APP_NAME: str = "ForensicGuard AI"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "127.0.0.1"

    # Database
    DATABASE_URL: str = "sqlite:///./forensic_cases.db"

    # Base Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    STORAGE_DIR: Path = BASE_DIR / "storage"
    ORIGINAL_UPLOADS_DIR: Path = BASE_DIR / "storage" / "originals"
    PROCESSED_MEDIA_DIR: Path = BASE_DIR / "storage" / "processed"
    ARTIFACTS_DIR: Path = BASE_DIR / "storage" / "artifacts"
    REPORTS_DIR: Path = BASE_DIR / "reports"
    WEIGHTS_DIR: Path = BASE_DIR / "weights"
    LOGS_DIR: Path = BASE_DIR / "logs"
    SOURCE_REPOSITORY_DIR: Path = BASE_DIR / "datasets" / "source_repository"

    # Execution Profile: FAST | BALANCED | DEEP_FORENSIC
    EXECUTION_PROFILE: str = "BALANCED"
    DEVICE: str = "cpu"

    # Model Weights Paths
    EFFICIENTNET_WEIGHTS: Path = WEIGHTS_DIR / "spatial_efficientnet_b0.pt"
    SWIN_WEIGHTS: Path = WEIGHTS_DIR / "temporal_swin_tiny.pt"
    WAV2VEC2_WEIGHTS: Path = WEIGHTS_DIR / "audio_wav2vec2_base.pt"
    DEBERTA_WEIGHTS: Path = WEIGHTS_DIR / "context_deberta_v3.pt"
    PPO_POLICY_WEIGHTS: Path = WEIGHTS_DIR / "ppo_orchestrator_policy.pt"

    # External APIs
    GDELT_API_KEY: str = ""
    GOOGLE_FACT_CHECK_API_KEY: str = ""
    NEWS_API_KEY: str = ""
    EVENT_REGISTRY_API_KEY: str = ""
    SOURCE_SEARCH_API_KEY: str = ""
    REVERSE_IMAGE_API_KEY: str = ""

    # Security & Upload Validation
    MAX_UPLOAD_SIZE_MB: int = 150
    ALLOWED_EXTENSIONS: List[str] = [
        "mp4", "mov", "avi", "mkv",
        "wav", "mp3", "flac", "m4a",
        "jpg", "jpeg", "png", "webp"
    ]

    # Forensic Verdict Thresholds
    THRESHOLD_LIKELY_FAKE: float = 0.65
    THRESHOLD_LIKELY_REAL: float = 0.35
    UNCERTAINTY_HIGH_THRESHOLD: float = 0.40
    UNCERTAINTY_MEDIUM_THRESHOLD: float = 0.20

    # Keyframe Extraction Limits by Profile
    PROFILE_KEYFRAMES: dict = {
        "FAST": 8,
        "BALANCED": 16,
        "DEEP_FORENSIC": 32,
    }

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def normalize_debug_value(cls, value):
        """Accept common deployment labels without making import-time startup brittle."""
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "production", "prod", "off"}:
                return False
            if normalized in {"development", "dev", "debug", "on"}:
                return True
        return value


settings = Settings()

# Ensure directories exist
for directory in [
    settings.STORAGE_DIR,
    settings.ORIGINAL_UPLOADS_DIR,
    settings.PROCESSED_MEDIA_DIR,
    settings.ARTIFACTS_DIR,
    settings.REPORTS_DIR,
    settings.REPORTS_DIR / "pdf",
    settings.REPORTS_DIR / "json",
    settings.WEIGHTS_DIR,
    settings.LOGS_DIR,
    settings.SOURCE_REPOSITORY_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)
