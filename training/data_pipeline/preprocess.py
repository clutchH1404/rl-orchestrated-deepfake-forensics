"""Lazy video/audio preparation primitives for training and evaluation datasets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from PIL import Image


@dataclass(frozen=True)
class SampledFrame:
    index: int
    timestamp_seconds: float
    image: Image.Image


def sample_video_frames(path: str | Path, count: int = 16, size: tuple[int, int] | None = (224, 224),
                        face_crop: bool = False) -> Iterator[SampledFrame]:
    """Uniformly sample frames, yielding RGB images and timestamps without retaining a full video."""
    if count < 1:
        raise ValueError("count must be at least 1")
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("Video sampling requires opencv-python-headless") from exc
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        capture.release()
        raise ValueError(f"Could not open video: {path}")
    try:
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        if frame_count <= 0:
            raise ValueError(f"Video has no readable frame count: {path}")
        indices = sorted(set(round(i * (frame_count - 1) / max(1, count - 1)) for i in range(count)))
        for index in indices:
            capture.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = capture.read()
            if not ok or frame is None:
                continue
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb)
            if face_crop:
                from backend.app.preprocessing.face_detector import FaceDetector
                import numpy as np
                box = FaceDetector().detect_face_bbox(np.asarray(image))
                y1, x1, y2, x2 = box
                image = image.crop((x1, y1, x2, y2))
            if size:
                image = image.resize(size, Image.Resampling.BILINEAR)
            yield SampledFrame(index, index / fps if fps > 0 else 0.0, image)
    finally:
        capture.release()


def load_audio(path: str | Path, target_sample_rate: int = 16000):
    """Load audio as mono float32 at target rate; returns (samples, sample_rate)."""
    try:
        import numpy as np
        import soundfile as sf
        from scipy.signal import resample_poly
    except ImportError as exc:
        raise RuntimeError("Audio loading requires soundfile and scipy") from exc
    audio, sample_rate = sf.read(str(path), dtype="float32", always_2d=True)
    mono = audio.mean(axis=1)
    if sample_rate != target_sample_rate:
        from math import gcd
        divisor = gcd(int(sample_rate), int(target_sample_rate))
        mono = resample_poly(mono, target_sample_rate // divisor, sample_rate // divisor).astype(np.float32)
    return mono, target_sample_rate
