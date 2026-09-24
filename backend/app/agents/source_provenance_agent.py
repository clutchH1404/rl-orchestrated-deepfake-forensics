"""Cautious source candidate retrieval for still images and extracted video frames."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import ExifTags, Image

from backend.app.core.config import settings
from backend.app.retrieval.local_repository import LocalRepositoryProvider
from backend.app.services.image_fingerprinting import crop_similarity, fingerprint, hamming_distance, structural_similarity


class SourceProvenanceAgent:
    """Ranks evidence-repository candidates without calling any candidate an original."""

    def __init__(self, repository_dir: Path | None = None):
        self.provider = LocalRepositoryProvider(repository_dir or settings.SOURCE_REPOSITORY_DIR)

    @staticmethod
    def analyze_metadata(image_path: Path) -> dict[str, Any]:
        with Image.open(image_path) as image:
            exif = {ExifTags.TAGS.get(k, str(k)): str(v) for k, v in image.getexif().items()}
            return {"filename": image_path.name, "dimensions": list(image.size), "format": image.format,
                    "mode": image.mode, "exif": exif, "icc_profile_present": bool(image.info.get("icc_profile")),
                    "embedded_thumbnail_candidate": False,
                    "note": "EXIF thumbnail extraction is not available in the baseline parser; no thumbnail is claimed."}

    def retrieve(self, image_path: Path, trigger: str = "MANUAL_RETRIEVAL") -> dict[str, Any]:
        query = fingerprint(image_path)
        candidates = []
        for candidate_path in self.provider.search_by_image(image_path):
            try:
                candidate = fingerprint(candidate_path)
                p_distance, d_distance = hamming_distance(query.phash, candidate.phash), hamming_distance(query.dhash, candidate.dhash)
                ssim, crop = structural_similarity(image_path, candidate_path), crop_similarity(image_path, candidate_path)
                # Similarity only ranks repository candidates; it does not establish provenance.
                score = 0.35 * (1 - p_distance / 64) + 0.15 * (1 - d_distance / 64) + 0.30 * ssim + 0.20 * crop
                label = "HIGH-CONFIDENCE SOURCE CANDIDATE" if score >= .88 else "POSSIBLE SOURCE CANDIDATE"
                candidates.append({"candidate_path": str(candidate_path), "provider": "local_repository", "classification": label,
                    "source_confidence": round(float(score), 4), "phash_distance": p_distance, "dhash_distance": d_distance,
                    "ahash_distance": hamming_distance(query.ahash, candidate.ahash), "structural_similarity": round(ssim, 4),
                    "crop_similarity": round(crop, 4), "query_dimensions": [query.width, query.height],
                    "candidate_dimensions": [candidate.width, candidate.height], "verification": "UNVERIFIED: visual similarity alone does not establish an original source."})
            except Exception as exc:
                candidates.append({"candidate_path": str(candidate_path), "classification": "UNAVAILABLE", "error": str(exc)})
        candidates.sort(key=lambda item: item.get("source_confidence", 0), reverse=True)
        return {"agent": "source_provenance_retrieval", "trigger": trigger, "generated_at": datetime.now(timezone.utc).isoformat(),
                "query_metadata": self.analyze_metadata(image_path), "query_fingerprint": {"ahash": query.ahash, "dhash": query.dhash, "phash": query.phash},
                "external_search": {"status": "UNAVAILABLE", "reason": "No permitted external provider is configured."},
                "candidates": candidates, "overall_status": "NO SOURCE FOUND" if not candidates else candidates[0]["classification"],
                "disclaimer": "Candidates are similarity-ranked leads, not verified originals. No AI reconstruction was used."}
