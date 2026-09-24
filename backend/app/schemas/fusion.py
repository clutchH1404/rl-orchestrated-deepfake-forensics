"""
Pydantic schemas for Cross-Modal Contradiction Analysis and Mathematical Evidence Fusion.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ContradictionEvidence(BaseModel):
    modality_a: str
    modality_b: str
    observation_a: str
    observation_b: str
    feature_divergence: float


class ContradictionItem(BaseModel):
    contradiction_id: str
    contradiction_type: str # e.g. "LIP_AUDIO_ASYNCHRONY", "SPEAKER_IDENTITY_MISMATCH", "TRANSCRIPT_VISUAL_CONFLICT"
    timestamp_start: float
    timestamp_end: float
    severity: str # "low", "medium", "high"
    confidence: float
    description: str
    evidence: List[ContradictionEvidence] = Field(default_factory=list)


class CrossModalResult(BaseModel):
    contradictions: List[ContradictionItem] = Field(default_factory=list)
    cross_modal_score: float = Field(ge=0.0, le=1.0) # 0.0 = completely contradictory, 1.0 = harmonious
    severity: str # "low", "medium", "high"
    evidence: List[str] = Field(default_factory=list)
    summary: str = ""


class UncertaintyResult(BaseModel):
    uncertainty_score: float = Field(ge=0.0, le=1.0) # Normalized entropy/variance
    uncertainty_level: str # "LOW", "MEDIUM", "HIGH"
    reason: str
    predictive_entropy: float
    ensemble_variance: float
    agent_disagreement_score: float


class EvidenceFusionResult(BaseModel):
    final_probability_fake: float = Field(ge=0.0, le=1.0)
    final_probability_real: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    agent_weights: Dict[str, float]
    uncertainty: float
    uncertainty_level: str # "LOW", "MEDIUM", "HIGH"
    uncertainty_reason: str
    verdict: str # "LIKELY AUTHENTIC", "LIKELY MANIPULATED", "INCONCLUSIVE"
    fusion_method: str = "RL-Calibrated Bayesian Evidence Fusion"
    disclaimer: str = "This system provides an AI-assisted forensic assessment and should not be treated as definitive proof of authenticity or manipulation."
