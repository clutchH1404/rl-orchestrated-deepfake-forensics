# Implementation Plan

## Completed baseline

- Runnable FastAPI application with health, model-status, case-intake, case-detail, and status endpoints.
- SQLite schema and chain-of-custody intake flow: uploads are size/extension checked, stored unchanged, hashed with SHA-256, and copied to an isolated processing directory.
- Metadata extraction avoids fabricated technical values when a media probe fails.
- Model-status API reports unavailable weights explicitly; no model or orchestration result is simulated.
- Source-provenance retrieval baseline: metadata inspection, perceptual hashes, local repository candidate ranking, and persisted cautious retrieval evidence.

## Next phases

1. Implement `ModelRegistry` and agent interfaces. Each wrapper will expose `available`, `mode`, and a typed unavailable result; model weights must be explicitly supplied and validated.
2. Add the asynchronous `ForensicPipeline`, agent-failure isolation, case-progress events, and preprocessing artifacts.
3. Implement measured spatial, temporal, audio, and context inference; keep training and evaluation code separate from production wrappers.
4. Add cross-modal consistency, uncertainty estimation, documented evidence fusion, and the PPO environment/training path.
5. Persist evidence/timeline/report artifacts and implement downloadable JSON/PDF reports.
6. Build the React forensic command center only against working API behavior; unavailable capabilities will be labelled accordingly.
7. Add evaluation, ablation, robustness scripts, and integration tests driven by real labelled data.

## Constraints recorded for reproducibility

- Host execution is CPU-oriented and no configured weights were found at audit time.
- Python 3.14 can constrain some ML wheel availability; use a supported Python 3.12 environment if PyTorch/transformer dependencies do not install cleanly.
- Datasets are configuration-only and must not be downloaded without explicit approval.
