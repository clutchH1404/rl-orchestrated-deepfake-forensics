from pathlib import Path

from backend.app.retrieval.base import SourceProvider


class LocalRepositoryProvider(SourceProvider):
    """Searches an explicitly configured, analyst-managed evidence repository."""
    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp"}

    def __init__(self, repository_dir: Path):
        self.repository_dir = repository_dir

    def search_by_image(self, image_path: Path) -> list[Path]:
        if not self.repository_dir.exists():
            return []
        return [p for p in self.repository_dir.rglob("*") if p.is_file() and p.suffix.lower() in self.allowed_extensions and p.resolve() != image_path.resolve()]
