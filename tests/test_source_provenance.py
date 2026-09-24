import shutil
from pathlib import Path

from PIL import Image

from backend.app.agents.source_provenance_agent import SourceProvenanceAgent
from backend.app.services.image_fingerprinting import fingerprint, hamming_distance


def _test_dir(name: str) -> Path:
    directory = Path("tests") / ".source_test_artifacts" / name
    shutil.rmtree(directory, ignore_errors=True)
    directory.mkdir(parents=True)
    return directory


def test_identical_local_candidate_is_ranked_but_not_declared_original():
    root = _test_dir("identical")
    query = root / "query.png"
    repository = root / "repository"
    repository.mkdir()
    candidate = repository / "candidate.png"
    image = Image.new("RGB", (40, 40), (20, 120, 200))
    image.save(query)
    image.save(candidate)
    result = SourceProvenanceAgent(repository).retrieve(query)
    assert result["overall_status"] == "HIGH-CONFIDENCE SOURCE CANDIDATE"
    assert result["candidates"][0]["verification"].startswith("UNVERIFIED")
    assert "original" not in result["candidates"][0]["classification"].lower()


def test_fingerprint_is_stable_for_same_image():
    image_path = _test_dir("fingerprint") / "image.png"
    Image.new("RGB", (24, 24), "navy").save(image_path)
    assert hamming_distance(fingerprint(image_path).phash, fingerprint(image_path).phash) == 0
