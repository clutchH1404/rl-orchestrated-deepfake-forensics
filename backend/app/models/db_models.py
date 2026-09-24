"""
SQLAlchemy database models for forensic cases, media integrity, agent results,
RL decisions, timeline events, and reports.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class CaseModel(Base):
    __tablename__ = "cases"

    case_id = Column(String(64), primary_key=True, index=True)
    title = Column(String(255), default="Forensic Verification Case")
    investigator = Column(String(255), default="Forensic Analyst")
    status = Column(String(50), default="INTAKE") # INTAKE, PREPROCESSING, ANALYZING, COMPLETED, FAILED
    progress = Column(Integer, default=0)
    current_stage = Column(String(100), default="Initialized")
    execution_profile = Column(String(50), default="BALANCED") # FAST, BALANCED, DEEP_FORENSIC

    verdict = Column(String(50), nullable=True) # LIKELY AUTHENTIC, LIKELY MANIPULATED, INCONCLUSIVE
    final_probability_fake = Column(Float, nullable=True)
    final_probability_real = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    uncertainty = Column(String(50), nullable=True)
    uncertainty_reason = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    media = relationship("MediaModel", back_populates="case", uselist=False, cascade="all, delete-orphan")
    agent_results = relationship("AgentResultModel", back_populates="case", cascade="all, delete-orphan")
    rl_decision = relationship("RLDecisionModel", back_populates="case", uselist=False, cascade="all, delete-orphan")
    timeline_events = relationship("TimelineEventModel", back_populates="case", cascade="all, delete-orphan")
    report = relationship("ReportModel", back_populates="case", uselist=False, cascade="all, delete-orphan")


class MediaModel(Base):
    __tablename__ = "media_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), unique=True, index=True)

    filename = Column(String(255), nullable=False)
    original_path = Column(String(1024), nullable=False)
    processed_path = Column(String(1024), nullable=False)
    original_sha256 = Column(String(64), nullable=False, index=True)
    processed_sha256 = Column(String(64), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    modality_type = Column(String(50), nullable=False) # video, audio, image

    duration_seconds = Column(Float, nullable=True)
    resolution = Column(String(50), nullable=True)
    fps = Column(Float, nullable=True)
    audio_sample_rate = Column(Integer, nullable=True)
    audio_channels = Column(Integer, nullable=True)
    has_video = Column(Boolean, default=False)
    has_audio = Column(Boolean, default=False)
    metadata_json = Column(Text, default="{}")

    created_at = Column(DateTime, default=utc_now)
    case = relationship("CaseModel", back_populates="media")


class AgentResultModel(Base):
    __tablename__ = "agent_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), index=True)
    agent_name = Column(String(50), nullable=False) # spatial_visual, temporal_visual, audio, context
    model_name = Column(String(100), nullable=False)
    prediction = Column(String(50), nullable=False)
    probability_fake = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    processing_time = Column(Float, default=0.0)
    result_json = Column(Text, nullable=False) # Serialized full agent schema

    created_at = Column(DateTime, default=utc_now)
    case = relationship("CaseModel", back_populates="agent_results")


class RLDecisionModel(Base):
    __tablename__ = "rl_decisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), unique=True, index=True)
    total_steps = Column(Integer, default=0)
    cumulative_reward = Column(Float, default=0.0)
    convergence_achieved = Column(Boolean, default=True)
    confidence_before = Column(Float, default=0.0)
    confidence_after = Column(Float, default=0.0)
    initial_weights_json = Column(Text, nullable=False)
    final_weights_json = Column(Text, nullable=False)
    trace_json = Column(Text, nullable=False)

    created_at = Column(DateTime, default=utc_now)
    case = relationship("CaseModel", back_populates="rl_decision")


class TimelineEventModel(Base):
    __tablename__ = "timeline_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), index=True)
    timestamp_seconds = Column(Float, nullable=False)
    formatted_time = Column(String(20), nullable=False)
    modality = Column(String(50), nullable=False)
    severity = Column(String(50), nullable=False) # low, medium, high, critical
    confidence = Column(Float, nullable=False)
    evidence = Column(Text, nullable=False)
    agent = Column(String(50), nullable=False)
    artifact_url = Column(String(1024), nullable=True)

    created_at = Column(DateTime, default=utc_now)
    case = relationship("CaseModel", back_populates="timeline_events")


class ReportModel(Base):
    __tablename__ = "forensic_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), unique=True, index=True)
    report_json = Column(Text, nullable=False)
    pdf_report_path = Column(String(1024), nullable=True)
    json_evidence_path = Column(String(1024), nullable=True)

    created_at = Column(DateTime, default=utc_now)
    case = relationship("CaseModel", back_populates="report")


class SourceRetrievalModel(Base):
    """Stored provenance search result; candidate status never implies authorship."""
    __tablename__ = "source_retrievals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), unique=True, index=True)
    status = Column(String(64), nullable=False)
    result_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now)
