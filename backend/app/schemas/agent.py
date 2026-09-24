"""
Pydantic schemas for the 4 Specialized Forensic Agents.
Adheres strictly to the specification in Sections 5, 6, 7, and 8.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class RegionAnomaly(BaseModel):
    frame_index: int
    timestamp_seconds: float
    bbox: List[int] # [ymin, xmin, ymax, xmax]
    anomaly_score: float
    description: str
    gradcam_path: Optional[str] = None


class SpatialVisualOutput(BaseModel):
    agent: str = "spatial_visual"
    model_name: str = "EfficientNet-B0"
    mode: str = "REAL MODEL INFERENCE (CPU-OPTIMIZED)"
    prediction: str # "real" or "fake"
    probability_fake: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    suspicious_frames: List[int] = Field(default_factory=list)
    regions: List[RegionAnomaly] = Field(default_factory=list)
    embedding: List[float] = Field(default_factory=list)
    processing_time: float = 0.0
    status: str = "COMPLETED"
    notes: Optional[str] = None


class TemporalAnomaly(BaseModel):
    segment_start: float
    segment_end: float
    motion_discontinuity: float
    flicker_score: float
    description: str


class TemporalVisualOutput(BaseModel):
    agent: str = "temporal_visual"
    model_name: str = "Swin-Tiny-Transformer"
    mode: str = "REAL MODEL INFERENCE (CPU-OPTIMIZED)"
    prediction: str # "real" or "fake"
    probability_fake: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    temporal_anomalies: List[TemporalAnomaly] = Field(default_factory=list)
    suspicious_segments: List[List[float]] = Field(default_factory=list) # [[start_sec, end_sec], ...]
    embedding: List[float] = Field(default_factory=list)
    processing_time: float = 0.0
    status: str = "COMPLETED"
    notes: Optional[str] = None


class SpectralEvidence(BaseModel):
    timestamp_seconds: float
    frequency_band_hz: str
    anomaly_type: str # e.g. "Synthetic High-Frequency Cutoff", "Robotic Phase Artifact"
    magnitude: float


class AudioOutput(BaseModel):
    agent: str = "audio"
    model_name: str = "wav2vec2-base"
    mode: str = "REAL MODEL INFERENCE (CPU-OPTIMIZED)"
    prediction: str # "real" or "fake"
    probability_fake: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    suspicious_segments: List[List[float]] = Field(default_factory=list)
    spectral_evidence: List[SpectralEvidence] = Field(default_factory=list)
    embedding: List[float] = Field(default_factory=list)
    processing_time: float = 0.0
    waveform_path: Optional[str] = None
    spectrogram_path: Optional[str] = None
    status: str = "COMPLETED"
    notes: Optional[str] = None


class FactClaim(BaseModel):
    claim_text: str
    speaker: Optional[str] = None
    timestamp_range: Optional[List[float]] = None
    verification_status: str # "VERIFIED", "REFUTED", "UNVERIFIED"
    contradiction_score: float
    source: Optional[str] = None


class ContextOutput(BaseModel):
    agent: str = "context"
    model_name: str = "DeBERTa-v3-base"
    mode: str = "REAL MODEL INFERENCE (CPU-OPTIMIZED)"
    prediction: str # "real" or "fake"
    probability_fake: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    transcript: str = ""
    claims: List[FactClaim] = Field(default_factory=list)
    entities: List[Dict[str, Any]] = Field(default_factory=list) # named entities: date, person, location
    external_verification: Dict[str, Any] = Field(default_factory=dict)
    embedding: List[float] = Field(default_factory=list)
    processing_time: float = 0.0
    status: str = "COMPLETED"
    notes: Optional[str] = None


class AgentCardSummary(BaseModel):
    agent: str
    title: str
    model: str
    status: str # "READY", "RUNNING", "COMPLETED", "SKIPPED", "FAILED"
    prediction: Optional[str] = None
    probability_fake: Optional[float] = None
    confidence: Optional[float] = None
    processing_time: Optional[float] = None
    evidence_count: int = 0
    trust_weight: float = 0.25
    mode: str = "REAL MODEL INFERENCE (CPU-OPTIMIZED)"
