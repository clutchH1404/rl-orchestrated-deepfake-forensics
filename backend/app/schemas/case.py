"""
Pydantic schemas for Forensic Cases and Media Intake.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class MediaMetadata(BaseModel):
    filename: str
    original_sha256: str
    processed_sha256: str
    file_size_bytes: int
    mime_type: str
    modality_type: str # "video", "audio", "image"
    duration_seconds: Optional[float] = None
    resolution: Optional[str] = None
    fps: Optional[float] = None
    audio_sample_rate: Optional[int] = None
    audio_channels: Optional[int] = None
    has_video: bool = False
    has_audio: bool = False
    extra_metadata: Dict[str, Any] = Field(default_factory=dict)


class CaseCreate(BaseModel):
    title: Optional[str] = "Forensic Verification Case"
    investigator: Optional[str] = "Forensic Analyst"
    execution_profile: Optional[str] = "BALANCED" # FAST, BALANCED, DEEP_FORENSIC
    notes: Optional[str] = None


class CaseStatusResponse(BaseModel):
    case_id: str
    status: str # "INTAKE", "PREPROCESSING", "ANALYZING", "COMPLETED", "FAILED"
    progress: int # 0 to 100
    current_stage: str
    error: Optional[str] = None
    updated_at: datetime


class CaseResponse(BaseModel):
    case_id: str
    title: str
    investigator: str
    status: str
    progress: int
    current_stage: str
    execution_profile: str
    created_at: datetime
    updated_at: datetime
    media: Optional[MediaMetadata] = None
    verdict: Optional[str] = None # "LIKELY AUTHENTIC", "LIKELY MANIPULATED", "INCONCLUSIVE"
    final_probability_fake: Optional[float] = None
    final_probability_real: Optional[float] = None
    confidence: Optional[float] = None
    uncertainty: Optional[str] = None
    error: Optional[str] = None
