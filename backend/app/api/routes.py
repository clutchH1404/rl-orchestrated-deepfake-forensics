"""REST endpoints available during the Phase 1 / intake baseline."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.app.core.database import Base, engine, get_db
from backend.app.core.config import settings
from backend.app.models.db_models import CaseModel, SourceRetrievalModel
from backend.app.agents.source_provenance_agent import SourceProvenanceAgent
from backend.app.preprocessing.media_extractor import MediaExtractor
import json
from pathlib import Path
from backend.app.schemas.case import CaseResponse, CaseStatusResponse
from backend.app.services.cases import create_case_from_upload, to_response

router = APIRouter(prefix="/api/v1", tags=["forensics"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.APP_NAME, "version": "1.0.0-research"}


@router.get("/models/status")
def model_status() -> dict:
    # Honest status only: no weights means inference is unavailable, not simulated.
    paths = {"spatial": settings.EFFICIENTNET_WEIGHTS, "temporal": settings.SWIN_WEIGHTS,
             "audio": settings.WAV2VEC2_WEIGHTS, "context": settings.DEBERTA_WEIGHTS,
             "ppo": settings.PPO_POLICY_WEIGHTS}
    return {"execution_profile": settings.EXECUTION_PROFILE, "device": settings.DEVICE,
            "models": {name: {"weights_available": path.exists(), "path": str(path)} for name, path in paths.items()},
            "inference_notice": "Model inference is unavailable until validated model weights are installed."}


@router.post("/cases", response_model=CaseResponse, status_code=201)
async def create_case(upload: UploadFile = File(...), title: str = Form("Forensic Verification Case"),
                      investigator: str = Form("Forensic Analyst"), execution_profile: str = Form("BALANCED"),
                      db: Session = Depends(get_db)) -> CaseResponse:
    return to_response(await create_case_from_upload(db, upload, title, investigator, execution_profile))


@router.get("/cases/{case_id}", response_model=CaseResponse)
def get_case(case_id: str, db: Session = Depends(get_db)) -> CaseResponse:
    case = db.get(CaseModel, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    return to_response(case)


@router.get("/cases/{case_id}/status", response_model=CaseStatusResponse)
def get_case_status(case_id: str, db: Session = Depends(get_db)) -> CaseStatusResponse:
    case = db.get(CaseModel, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    return CaseStatusResponse(case_id=case.case_id, status=case.status, progress=case.progress,
        current_stage=case.current_stage, error=case.error_message, updated_at=case.updated_at)


@router.post("/cases/{case_id}/source-retrieval")
def run_source_retrieval(case_id: str, db: Session = Depends(get_db)) -> dict:
    """Manually search configured evidence repositories for cautiously ranked image leads."""
    case = db.get(CaseModel, case_id)
    if not case or not case.media:
        raise HTTPException(status_code=404, detail="Case or media not found.")
    media = case.media
    if media.modality_type == "audio":
        raise HTTPException(status_code=422, detail="Source image retrieval requires image or video media.")
    query_path = Path(media.processed_path)
    if media.modality_type == "video":
        frames = MediaExtractor(query_path, case_id).extract_keyframes(1)
        if not frames:
            raise HTTPException(status_code=422, detail="No retrievable video frame was extracted.")
        query_path = frames[0][2]
    result = SourceProvenanceAgent().retrieve(query_path)
    existing = db.query(SourceRetrievalModel).filter_by(case_id=case_id).one_or_none()
    if existing:
        existing.status, existing.result_json = result["overall_status"], json.dumps(result)
    else:
        db.add(SourceRetrievalModel(case_id=case_id, status=result["overall_status"], result_json=json.dumps(result)))
    db.commit()
    return result


@router.get("/cases/{case_id}/source-retrieval")
def get_source_retrieval(case_id: str, db: Session = Depends(get_db)) -> dict:
    record = db.query(SourceRetrievalModel).filter_by(case_id=case_id).one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="No source retrieval has been run for this case.")
    return json.loads(record.result_json)
