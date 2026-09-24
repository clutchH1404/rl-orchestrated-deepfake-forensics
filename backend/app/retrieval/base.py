from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class SourceProvider(ABC):
    """Provider contract. Providers return candidates, never asserted originals."""

    @abstractmethod
    def search_by_image(self, image_path: Path) -> list[Path]: ...

    def search_by_hash(self, _: str) -> list[Path]:
        return []

    def search_by_embedding(self, _: list[float]) -> list[Path]:
        return []

    def get_candidate_metadata(self, candidate: Path) -> dict[str, Any]:
        return {"filename": candidate.name, "provider": self.__class__.__name__}
