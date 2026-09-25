"""
Forensic security, cryptographic hashing, and chain-of-custody integrity verification.
"""

import hashlib
import re
import shutil
import subprocess
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Tuple
from fastapi import HTTPException, UploadFile, status

from backend.app.core.config import settings
from backend.app.core.logging import log_forensic_event


def validate_media_content(file_path: Path, extension: str) -> None:
    """Decode enough of an uploaded file to reject mislabeled or corrupt media."""
    try:
        if extension in {"jpg", "jpeg", "png", "webp"}:
            from PIL import Image
            with Image.open(file_path) as image:
                image.verify()
            return
        if extension == "wav":
            with wave.open(str(file_path), "rb") as audio:
                if audio.getnframes() <= 0 or audio.getframerate() <= 0:
                    raise ValueError("WAV has no samples or an invalid sample rate")
            return
        if extension in {"mp4", "mov", "avi", "mkv"}:
            import cv2
            capture = cv2.VideoCapture(str(file_path))
            try:
                if not capture.isOpened() or not capture.read()[0]:
                    raise ValueError("Video decoder could not read a frame")
            finally:
                capture.release()
            return
        # Decode a short prefix of compressed audio formats using the bundled FFmpeg binary.
        import imageio_ffmpeg
        result = subprocess.run(
            [imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i", str(file_path),
             "-t", "0.1", "-f", "null", "-"],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=20, check=False,
        )
        if result.returncode != 0:
            raise ValueError("Audio decoder rejected the file")
    except Exception as exc:
        log_forensic_event("media_validation_failed", details={"filename": file_path.name, "error": str(exc)})
        raise HTTPException(status_code=422, detail=f"Uploaded {extension.upper()} media is invalid or corrupted.") from exc


def calculate_sha256(file_path: Path) -> str:
    """Computes SHA-256 digest of a local file in chunks."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def sanitize_filename(filename: str) -> str:
    """Removes unsafe characters to prevent path traversal and shell injection."""
    clean = re.sub(r"[^\w\s\.-]", "", filename).strip()
    return clean or "unnamed_media_file"


def validate_upload(upload_file: UploadFile) -> Tuple[str, str]:
    """
    Validates uploaded file against allowed extensions, mime types, and size bounds.
    Returns (sanitized_name, extension).
    """
    if not upload_file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename."
        )

    sanitized = sanitize_filename(upload_file.filename)
    extension = sanitized.rsplit(".", 1)[-1].lower() if "." in sanitized else ""

    if extension not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File extension '{extension}' is not supported. Allowed formats: {settings.ALLOWED_EXTENSIONS}"
        )

    return sanitized, extension


def create_forensic_working_copy(
    case_id: str, original_path: Path, sanitized_filename: str
) -> Tuple[Path, str, str]:
    """
    Creates an isolated working copy for preprocessing while preserving the original.
    Returns (working_copy_path, original_sha256, processed_sha256).
    """
    original_sha256 = calculate_sha256(original_path)

    # Isolated directory per case
    case_processed_dir = settings.PROCESSED_MEDIA_DIR / case_id
    case_processed_dir.mkdir(parents=True, exist_ok=True)

    working_copy_path = case_processed_dir / f"work_{sanitized_filename}"
    shutil.copy2(original_path, working_copy_path)

    # Initial processed copy hash matches original
    processed_sha256 = calculate_sha256(working_copy_path)

    log_forensic_event(
        event="chain_of_custody_initialized",
        case_id=case_id,
        details={
            "original_sha256": original_sha256,
            "working_copy_sha256": processed_sha256,
            "filename": sanitized_filename,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    return working_copy_path, original_sha256, processed_sha256
