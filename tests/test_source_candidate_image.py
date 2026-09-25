import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from PIL import Image

from backend.app.api.routes import get_source_candidate_image
from backend.app.core.config import settings


class _Query:
    def __init__(self, record):
        self.record = record

    def filter_by(self, **_kwargs):
        return self

    def one_or_none(self):
        return self.record


class _DB:
    def __init__(self, record):
        self.record = record

    def query(self, _model):
        return _Query(self.record)


def test_candidate_image_endpoint_serves_only_repository_candidate(tmp_path, monkeypatch):
    repository = tmp_path / "repository"
    repository.mkdir()
    candidate = repository / "match.png"
    Image.new("RGB", (8, 8), "navy").save(candidate)
    monkeypatch.setattr(settings, "SOURCE_REPOSITORY_DIR", repository)
    result = {"candidates": [{"provider": "local_repository", "candidate_path": str(candidate)}]}
    response = get_source_candidate_image("case-1", 0, _DB(SimpleNamespace(result_json=json.dumps(result))))
    assert response.path == candidate
    with pytest.raises(HTTPException) as exc:
        get_source_candidate_image("case-1", 1, _DB(SimpleNamespace(result_json=json.dumps(result))))
    assert exc.value.status_code == 404


def test_candidate_image_endpoint_rejects_paths_outside_repository(tmp_path, monkeypatch):
    repository = tmp_path / "repository"
    repository.mkdir()
    outside = tmp_path / "outside.png"
    Image.new("RGB", (8, 8), "black").save(outside)
    monkeypatch.setattr(settings, "SOURCE_REPOSITORY_DIR", repository)
    result = {"candidates": [{"provider": "local_repository", "candidate_path": str(outside)}]}
    with pytest.raises(HTTPException) as exc:
        get_source_candidate_image("case-1", 0, _DB(SimpleNamespace(result_json=json.dumps(result))))
    assert exc.value.status_code == 404
