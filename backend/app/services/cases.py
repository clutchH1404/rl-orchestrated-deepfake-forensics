"""Case-intake service. Preserves source evidence and records its custody trail."""

import json
import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.logging import log_forensic_event
from backend.app.core.security import create_forensic_working_copy, validate_upload
from backend.app.models.db_models import CaseModel, MediaModel
from backend.app.preprocessing.media_extractor import MediaExtractor
from backend.app.schemas.case import CaseResponse, MediaMetadata


def _profile(value: str) -> str:
    profile = value.upper()
    if profile not in settings.PROFILE_KEYFRAMES:
        raise HTTPException(status_code=422, detail="execution_profile must be FAST, BALANCED, or DEEP_FORENSIC.")
    return profile


def _metadata_from_model(media: MediaModel) -> MediaMetadata:
    return MediaMetadata(
        filename=media.filename,
        original_sha256=media.original_sha256,
        processed_sha256=media.processed_sha256,
        file_size_bytes=media.file_size_bytes,
        mime_type=media.mime_type,
        modality_type=media.modality_type,
        duration_seconds=media.duration_seconds,
        resolution=media.resolution,
        fps=media.fps,
        audio_sample_rate=media.audio_sample_rate,
        audio_channels=media.audio_channels,
        has_video=media.has_video,
        has_audio=media.has_audio,
        extra_metadata=json.loads(media.metadata_json or "{}"),
    )


def to_response(case: CaseModel) -> CaseResponse:
    return CaseResponse(
        case_id=case.case_id, title=case.title, investigator=case.investigator,
        status=case.status, progress=case.progress, current_stage=case.current_stage,
        execution_profile=case.execution_profile, created_at=case.created_at,
        updated_at=case.updated_at, media=_metadata_from_model(case.media) if case.media else None,
        verdict=case.verdict, final_probability_fake=case.final_probability_fake,
        final_probability_real=case.final_probability_real, confidence=case.confidence,
        uncertainty=case.uncertainty, error=case.error_message,
    )


async def create_case_from_upload(
    db: Session, upload: UploadFile, title: str, investigator: str, execution_profile: str,
) -> CaseModel:
    filename, _ = validate_upload(upload)
    profile = _profile(execution_profile)
    case_id = uuid.uuid4().hex
    original_dir = settings.ORIGINAL_UPLOADS_DIR / case_id
    original_dir.mkdir(parents=True, exist_ok=False)
    original_path = original_dir / filename
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    written = 0

    try:
        with original_path.open("xb") as destination:
            while chunk := await upload.read(1024 * 1024):
                written += len(chunk)
                if written > max_bytes:
                    raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit.")
                destination.write(chunk)
        working_path, original_hash, processed_hash = create_forensic_working_copy(case_id, original_path, filename)
        extractor = MediaExtractor(working_path, case_id)
        metadata = extractor.extract_metadata(original_hash, processed_hash)
        case = CaseModel(case_id=case_id, title=title, investigator=investigator,
                         execution_profile=profile, status="INTAKE", progress=10,
                         current_stage="Media integrity and metadata captured")
        db.add(case)
        db.add(MediaModel(case_id=case_id, filename=filename, original_path=str(original_path),
            processed_path=str(working_path), original_sha256=original_hash, processed_sha256=processed_hash,
            file_size_bytes=metadata.file_size_bytes, mime_type=metadata.mime_type,
            modality_type=metadata.modality_type, duration_seconds=metadata.duration_seconds,
            resolution=metadata.resolution, fps=metadata.fps, audio_sample_rate=metadata.audio_sample_rate,
            audio_channels=metadata.audio_channels, has_video=metadata.has_video, has_audio=metadata.has_audio,
            metadata_json=json.dumps(metadata.extra_metadata)))
        db.commit()
        db.refresh(case)
        log_forensic_event("case_intake_completed", case_id=case_id, details={"modality": metadata.modality_type, "bytes": written})
        return case
    except HTTPException:
        db.rollback()
        shutil.rmtree(original_dir, ignore_errors=True)
        shutil.rmtree(settings.PROCESSED_MEDIA_DIR / case_id, ignore_errors=True)
        raise
    except Exception as exc:
        db.rollback()
        shutil.rmtree(original_dir, ignore_errors=True)
        shutil.rmtree(settings.PROCESSED_MEDIA_DIR / case_id, ignore_errors=True)
        log_forensic_event("case_intake_failed", case_id=case_id, details={"error": str(exc)})
        raise HTTPException(status_code=500, detail="Unable to initialize forensic case.") from exc
