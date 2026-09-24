# VERITAS — RL-Orchestrated Media Forensics

VERITAS is a capstone-oriented, production-style foundation for multimodal deepfake forensic investigation. It preserves chain of custody, records media metadata, exposes an API-driven command-center UI, and supports cautious local source-candidate retrieval.

> This system provides an AI-assisted forensic assessment and should not be treated as definitive proof of authenticity or manipulation.

## Current capabilities

- Secure media intake for video, audio, and images, with extension/size validation and filename sanitization.
- SHA-256 chain of custody: immutable uploaded original, isolated processing copy, and persisted metadata.
- FastAPI service with health, model-status, case, case-status, and source-retrieval endpoints.
- SQLite persistence for cases, media, agent results, RL decisions, evidence timelines, reports, and source-retrieval records.
- Image source-candidate retrieval against an analyst-controlled local repository using aHash, dHash, pHash, SSIM, and crop similarity.
- A functional zero-build VERITAS frontend for intake, live model availability, custody metadata, and source-retrieval results.

## Deliberate research-integrity boundaries

No synthetic ML predictions, source matches, confidence values, or explainability artifacts are presented as real evidence. Model weights are currently not bundled: the API marks all unavailable models accordingly. The source-retrieval agent produces leads only—it never labels a candidate as a verified original.

Pretrained visual/temporal/audio/context wrappers, PPO training, cross-modal fusion, report generation, face-aware matching, and external reverse-image providers remain planned work. See [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md).

## Run locally

Requirements: Python 3.12+ recommended (the audited environment uses Python 3.14), plus dependencies in `backend/requirements.txt`.

```powershell
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload
```

In another terminal, serve the frontend:

```powershell
python -m http.server 5173 --directory frontend
```

Open the frontend at `http://localhost:5173`, API docs at `http://127.0.0.1:8000/docs`, and health status at `http://127.0.0.1:8000/api/v1/health`.

## Source candidate retrieval

Place investigator-authorized reference images under `datasets/source_repository/`, then create an image/video case and choose **Search Local Sources** in the frontend. The API endpoint is:

```text
POST /api/v1/cases/{case_id}/source-retrieval
```

Read [docs/SOURCE_PROVENANCE_RETRIEVAL.md](docs/SOURCE_PROVENANCE_RETRIEVAL.md) before interpreting any candidate.

## Test

```powershell
python -m pytest -q
```

## Repository layout

```text
backend/     FastAPI API, custody services, schemas, persistence, and agents
frontend/    VERITAS command-center interface
configs/     Pipeline and dataset configuration
docs/        Audit, architecture planning, and provenance methodology
tests/       API and source-retrieval tests
```
