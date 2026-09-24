# Source Provenance Retrieval

The source-provenance agent is a lead-generation tool, not an origin-proof tool. It currently searches only the analyst-controlled local repository at `datasets/source_repository`. It computes aHash, dHash, DCT pHash, global SSIM, and center-crop similarity for every candidate.

Candidates are ranked by a documented weighted score:

`0.35 × pHash similarity + 0.15 × dHash similarity + 0.30 × SSIM + 0.20 × crop similarity`

Scores label a result as `HIGH-CONFIDENCE SOURCE CANDIDATE` (at least 0.88), `POSSIBLE SOURCE CANDIDATE`, or `NO SOURCE FOUND`. A `VERIFIED SOURCE` is intentionally never assigned by this automated baseline. Human review and independently verifiable provenance are required.

Use `POST /api/v1/cases/{case_id}/source-retrieval` for an image case, or a video case to search with an extracted representative frame. The endpoint is manual until the visual-forensics pipeline produces a real manipulation result. It never presumes manipulation and does not use AI reconstruction.

External reverse-image/source providers are deliberately unimplemented until a legally permitted provider, API adapter, and user-provided credentials are configured. Their absence is returned as `EXTERNAL SEARCH: UNAVAILABLE`.
