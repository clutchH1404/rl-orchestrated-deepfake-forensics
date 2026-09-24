"""
Pydantic schemas for the Reinforcement Learning (PPO) Meta-Agent Controller.
"""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class AgentTrustWeights(BaseModel):
    spatial: float = Field(ge=0.0, le=1.0, default=0.25)
    temporal: float = Field(ge=0.0, le=1.0, default=0.25)
    audio: float = Field(ge=0.0, le=1.0, default=0.25)
    context: float = Field(ge=0.0, le=1.0, default=0.25)


class RLState(BaseModel):
    spatial_confidence: float
    temporal_confidence: float
    audio_confidence: float
    context_confidence: float
    cross_modal_consistency: float
    uncertainty: float
    previous_decision: float # 0.0=real, 1.0=fake
    modality_availability: float # Bitmask or ratio of active modalities (e.g. 1.0 for all 4)


class RLActionStep(BaseModel):
    step: int
    action_id: int
    action_name: str
    reward: float
    value_estimate: float
    weights_before: AgentTrustWeights
    weights_after: AgentTrustWeights
    state_vector: List[float]


class RLExecutionTrace(BaseModel):
    initial_weights: AgentTrustWeights
    final_weights: AgentTrustWeights
    total_steps: int
    cumulative_reward: float
    convergence_achieved: bool
    action_history: List[RLActionStep] = Field(default_factory=list)
    confidence_before_rl: float
    confidence_after_rl: float
    disagreement_resolved: float
    rl_agent_type: str = "PPO (Proximal Policy Optimization)"
