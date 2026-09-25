"""CLI: python -m training.data_pipeline.build_manifest [config] [output]"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .manifest import DatasetManifestBuilder


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local dataset manifest; no data is downloaded.")
    parser.add_argument("--config", default="configs/datasets.yaml")
    parser.add_argument("--output", default="datasets/manifests/train.jsonl")
    parser.add_argument("--include-disabled", action="store_true")
    args = parser.parse_args()
    builder = DatasetManifestBuilder(args.config)
    records = builder.build(include_disabled=args.include_disabled)
    summary = builder.write(records, args.output)
    print(json.dumps({"manifest": str(Path(args.output).resolve()), "summary": summary,
                      "missing_paths": builder.missing_paths,
                      "unlabeled_files_skipped": builder.unlabeled_files}, indent=2))


if __name__ == "__main__":
    main()
