import json
from pathlib import Path

from PIL import Image

from training.data_pipeline.augment import MediaAugmenter
from training.data_pipeline.manifest import DatasetManifestBuilder


def test_manifest_reads_local_records_and_keeps_groups_together(tmp_path):
    root = tmp_path / "datasets" / "toy"
    (root / "real").mkdir(parents=True)
    (root / "fake").mkdir()
    (root / "real" / "pair01.mp4").touch()
    (root / "fake" / "pair01_swap.mp4").touch()
    config = tmp_path / "configs" / "datasets.yaml"
    config.parent.mkdir()
    config.write_text("""datasets:\n  toy:\n    enabled: true\n    base_path: ./datasets/toy\n    modalities: [video]\n    subsets:\n      real: real\n      fake: fake\npipeline:\n  seed: 9\n  split_ratios: {train: 0.8, validation: 0.1, test: 0.1}\n""", encoding="utf-8")

    builder = DatasetManifestBuilder(config)
    records = builder.build()
    assert len(records) == 2
    assert {r.label for r in records} == {0, 1}
    assert len({r.split for r in records}) == 1
    output = tmp_path / "manifest.jsonl"
    summary = builder.write(records, output)
    assert len(DatasetManifestBuilder.read(output)) == 2
    assert summary["records"] == 2
    assert json.loads(output.with_suffix(".summary.json").read_text())["records"] == 2


def test_dfdc_metadata_labels_and_unknowns(tmp_path):
    root = tmp_path / "datasets" / "dfdc"
    root.mkdir(parents=True)
    (root / "000.mp4").touch()
    (root / "001.mp4").touch()
    (root / "metadata.json").write_text(json.dumps({
        "000.mp4": {"label": "REAL"}, "001.mp4": {"label": "FAKE"}
    }), encoding="utf-8")
    config = tmp_path / "configs" / "datasets.yaml"
    config.parent.mkdir()
    config.write_text("""datasets:\n  dfdc:\n    enabled: true\n    base_path: ./datasets/dfdc\n    modalities: [video, audio]\n    metadata_files: [metadata.json]\n    subsets: {videos: .}\npipeline: {}\n""", encoding="utf-8")
    records = DatasetManifestBuilder(config).build()
    assert {Path(r.path).name: r.label for r in records} == {"000.mp4": 0, "001.mp4": 1}


def test_image_augment_is_seeded_and_keeps_dimensions():
    image = Image.new("RGB", (32, 24), "gray")
    config = {"jpeg_probability": 1, "jpeg_quality": [70, 70], "blur_probability": 0,
              "brightness_probability": 0}
    left = MediaAugmenter(123, config).image(image)
    right = MediaAugmenter(123, config).image(image)
    assert left.size == (32, 24)
    assert list(left.get_flattened_data()) == list(right.get_flattened_data())
