"""
Pydantic schemas for the Forensic Evidence Timeline and Final Forensic Report.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from backend.app.schemas.case import MediaMetadata
from backend.app.schemas.agent import (
    SpatialVisualOutput,
    TemporalVisualOutput,
    AudioOutput,
    ContextOutput,
)
from backend.app.schemas.rl import RLExecutionTrace
from backend.app.schemas.fusion import CrossModalResult, EvidenceFusionResult


class TimelineEvent(BaseModel):
    event_id: str
    timestamp_seconds: float
    formatted_time: str # "00:04"
    modality: str # "visual", "temporal", "audio", "context", "cross-modal"
    severity: str # "low", "medium", "high", "critical"
    confidence: float
    evidence: str
    agent: str
    artifact_url: Optional[str] = None # Path to Grad-CAM thumbnail or spectrogram snapshot


class ChainOfCustodyRecord(BaseModel):
    original_sha256: str
    processed_sha256: str
    intake_timestamp: str
    verification_hash_match: bool
    analyst_signature: str = "ForensicGuard Autonomous Multi-Agent Pipeline"


class ForensicReportSchema(BaseModel):
    report_id: str
    case_id: str
    generated_at: str
    system_version: str = "ForensicGuard v1.0 (RL-Orchestrated)"
    media_metadata: MediaMetadata
    chain_of_custody: ChainOfCustodyRecord

    # Verdict & Intelligence
    verdict: str
    confidence: float
    uncertainty: str
    uncertainty_reason: str

    # Agent Breakdown
    spatial_agent: Optional[SpatialVisualOutput] = None
    temporal_agent: Optional[TemporalVisualOutput] = None
    audio_agent: Optional[AudioOutput] = None
    context_agent: Optional[ContextOutput] = None

    # RL Orchestration & Fusion
    rl_trace: Optional[RLExecutionTrace] = None
    cross_modal_analysis: Optional[CrossModalResult] = None
    fusion_result: Optional[EvidenceFusionResult] = None

    # Evidence & Timeline
    timeline_events: List[TimelineEvent] = Field(default_factory=list)
    methodology: str
    limitations: List[str]
    disclaimer: str = (
        "This system provides an AI-assisted forensic assessment and should not be "
        "treated as definitive proof of authenticity or manipulation."
    )
    pdf_report_path: Optional[str] = None
    json_evidence_package_path: Optional[str] = None
