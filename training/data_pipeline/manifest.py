"""Build normalized, reproducible manifests from locally available datasets."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class DatasetRecord:
    path: str
    dataset: str
    label: int
    manipulation_type: str
    modalities: tuple[str, ...]
    split: str
    group_id: str
    subset: str


class DatasetManifestBuilder:
    """Discover configured local files and assign deterministic group splits."""

    def __init__(self, config_path: str | Path, seed: int | None = None):
        self.config_path = Path(config_path).resolve()
        with self.config_path.open("r", encoding="utf-8") as stream:
            self.config = yaml.safe_load(stream) or {}
        self.root = self.config_path.parent.parent
        options = self.config.get("pipeline", {})
        self.seed = int(seed if seed is not None else options.get("seed", 42))
        self.missing_paths: list[str] = []
        self.unlabeled_files: list[str] = []

    def build(self, include_disabled: bool = False) -> list[DatasetRecord]:
        records: list[DatasetRecord] = []
        for key, dataset in self.config.get("datasets", {}).items():
            if not dataset.get("enabled", False) and not include_disabled:
                continue
            base = self._resolve(dataset.get("base_path", ""))
            if not base.is_dir():
                self.missing_paths.append(str(base))
                continue
            modalities = tuple(dataset.get("modalities", ()))
            extensions = tuple(dataset.get("extensions", (".mp4", ".mov", ".mkv", ".avi", ".webm", ".jpg", ".jpeg", ".png", ".wav", ".flac")))
            metadata_labels = self._metadata_labels(base, dataset.get("metadata_files", []))
            official_splits = self._official_splits(base, dataset.get("evaluation_split"))
            subsets = dataset.get("subsets", {})
            if subsets:
                candidates = ((str(name), base / str(relative)) for name, relative in subsets.items())
            else:
                candidates = (("data", base),)
            for subset, folder in candidates:
                if not folder.is_dir():
                    self.missing_paths.append(str(folder))
                    continue
                for path in sorted(folder.rglob("*")):
                    if path.is_file() and path.suffix.lower() in extensions:
                        configured_label = dataset.get("labels", {}).get(subset)
                        label_value = configured_label if configured_label is not None else metadata_labels.get(path.name)
                        if label_value is None:
                            if dataset.get("metadata_files"):
                                continue  # Unknown DFDC rows are never silently treated as authentic.
                            label_value = self._infer_label(subset)
                        if label_value is None:
                            self.unlabeled_files.append(str(path.resolve()))
                            continue
                        label = self._label(str(label_value))
                        manipulation = str(dataset.get("manipulation_types", {}).get(subset, self._infer_manipulation(subset, label)))
                        # Paired/source clips often share an ID prefix; group conservatively.
                        group_id = str(dataset.get("group_ids", {}).get(path.name, self._group_id(path.stem)))
                        records.append(DatasetRecord(str(path.resolve()), key, label, manipulation,
                                                     modalities, official_splits.get(path.name, official_splits.get(path.stem, "")), group_id, subset))
        return self._assign_splits(records)

    def write(self, records: list[DatasetRecord], manifest_path: str | Path) -> dict[str, Any]:
        target = Path(manifest_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8", newline="\n") as stream:
            for record in records:
                stream.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
        summary = self.summarize(records)
        summary_path = target.with_suffix(".summary.json")
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary

    @staticmethod
    def read(manifest_path: str | Path) -> list[DatasetRecord]:
        records = []
        with Path(manifest_path).open("r", encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    item = json.loads(line)
                    item["modalities"] = tuple(item.get("modalities", ()))
                    records.append(DatasetRecord(**item))
        return records

    @staticmethod
    def summarize(records: list[DatasetRecord]) -> dict[str, Any]:
        def counts(key):
            result: dict[str, int] = {}
            for record in records:
                value = str(key(record))
                result[value] = result.get(value, 0) + 1
            return result
        return {"records": len(records), "splits": counts(lambda r: r.split),
                "labels": counts(lambda r: r.label), "datasets": counts(lambda r: r.dataset),
                "manipulation_types": counts(lambda r: r.manipulation_type),
                "modalities": counts(lambda r: "+".join(r.modalities))}

    def _assign_splits(self, records: list[DatasetRecord]) -> list[DatasetRecord]:
        # Dataset splits take precedence; otherwise all related group members share a stable split.
        split_map = self.config.get("pipeline", {}).get("split_map", {})
        ratios = self.config.get("pipeline", {}).get("split_ratios", {"train": .8, "validation": .1, "test": .1})
        total = sum(float(ratios.get(k, 0)) for k in ("train", "validation", "test")) or 1
        cut1 = float(ratios.get("train", .8)) / total
        cut2 = cut1 + float(ratios.get("validation", .1)) / total
        assigned = []
        for row in records:
            explicit = row.split or split_map.get(row.path) or split_map.get(Path(row.path).name)
            if explicit:
                split = explicit
            else:
                digest = hashlib.sha256(f"{self.seed}:{row.dataset}:{row.group_id}".encode()).digest()
                value = int.from_bytes(digest[:8], "big") / 2**64
                split = "train" if value < cut1 else "validation" if value < cut2 else "test"
            assigned.append(DatasetRecord(**{**asdict(row), "split": split}))
        return assigned

    def _resolve(self, value: str) -> Path:
        path = Path(value)
        return path.resolve() if path.is_absolute() else (self.root / path).resolve()

    @staticmethod
    def _metadata_labels(base: Path, metadata_files: list[str]) -> dict[str, str]:
        """Read DFDC-style metadata.json maps without assuming a single shard layout."""
        labels: dict[str, str] = {}
        for relative in metadata_files:
            candidate = base / relative
            files = sorted(base.rglob(Path(relative).name)) if not candidate.exists() else [candidate]
            for metadata_file in files:
                try:
                    data = json.loads(metadata_file.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if not isinstance(data, dict):
                    continue
                for filename, attributes in data.items():
                    if isinstance(attributes, dict) and attributes.get("label") is not None:
                        labels[Path(filename).name] = str(attributes["label"])
        return labels

    @staticmethod
    def _official_splits(base: Path, split_file: str | None) -> dict[str, str]:
        """Read keyed split maps and the common FF++ [train, validation, test] format."""
        if not split_file:
            return {}
        path = base / split_file
        if not path.is_file():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        result: dict[str, str] = {}
        groups = payload.items() if isinstance(payload, dict) else zip(("train", "validation", "test"), payload) if isinstance(payload, list) else []
        for split, members in groups:
            split = str(split).lower()
            canonical = "validation" if split in {"val", "valid", "dev"} else split
            if isinstance(members, str):
                members = [members]
            if not isinstance(members, list):
                continue
            for member in members:
                values = member if isinstance(member, (list, tuple)) else [member]
                for value in values:
                    if isinstance(value, str):
                        result[Path(value).name] = canonical
                        result[Path(value).stem] = canonical
        return result

    @staticmethod
    def _label(value: Any) -> int:
        if isinstance(value, int) and value in (0, 1):
            return value
        token = str(value).lower()
        if token in {"real", "authentic", "original", "pristine", "0"}: return 0
        if token in {"fake", "manipulated", "synthetic", "1"}: return 1
        raise ValueError(f"Label must map to 0 (real) or 1 (manipulated), got {value!r}")

    @staticmethod
    def _infer_label(subset: str) -> str | None:
        token = subset.lower()
        if any(word in token for word in ("fake", "synthesis", "manipulated", "deepfake", "face2face", "faceswap", "neuraltexture")):
            return "fake"
        if any(word in token for word in ("real", "authentic", "original", "pristine", "youtube")):
            return "real"
        return None

    @staticmethod
    def _infer_manipulation(subset: str, label: int) -> str:
        if not label: return "none"
        token = subset.lower()
        for name in ("deepfakes", "face2face", "faceswap", "faceshifter", "neuraltextures", "synthesis"):
            if name in token: return name
        return "unspecified"

    @staticmethod
    def _group_id(stem: str) -> str:
        # FF++ manipulated filenames commonly contain source/target IDs; keep a
        # shared source prefix in one split so source footage cannot leak across splits.
        return stem.split("_", 1)[0] if "_" in stem else stem
