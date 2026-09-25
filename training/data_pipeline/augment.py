"""Seedable train-only augmentations; evaluation data should bypass this module."""

from __future__ import annotations

import random
from io import BytesIO

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter


class MediaAugmenter:
    def __init__(self, seed: int = 42, config: dict | None = None):
        self.rng = random.Random(seed)
        self.config = config or {}

    def image(self, image: Image.Image) -> Image.Image:
        """Apply configured mild blur, brightness, and JPEG re-encoding with deterministic RNG."""
        result = image.convert("RGB")
        if self.rng.random() < float(self.config.get("jpeg_probability", 0.5)):
            quality = self.rng.randint(*self.config.get("jpeg_quality", [45, 90]))
            buffer = BytesIO()
            result.save(buffer, format="JPEG", quality=quality)
            buffer.seek(0)
            result = Image.open(buffer).convert("RGB")
        if self.rng.random() < float(self.config.get("blur_probability", 0.1)):
            result = result.filter(ImageFilter.GaussianBlur(self.rng.uniform(0.1, 1.2)))
        if self.rng.random() < float(self.config.get("brightness_probability", 0.25)):
            result = ImageEnhance.Brightness(result).enhance(self.rng.uniform(0.8, 1.2))
        return result

    def audio(self, samples: np.ndarray) -> np.ndarray:
        """Apply configured gain and low-level noise; caller retains original sample rate."""
        result = np.asarray(samples, dtype=np.float32).copy()
        if self.rng.random() < float(self.config.get("gain_probability", 0.3)):
            result *= self.rng.uniform(0.75, 1.25)
        if self.rng.random() < float(self.config.get("noise_probability", 0.2)):
            scale = float(self.config.get("noise_std", 0.003))
            noise = np.random.default_rng(self.rng.randrange(2**32)).normal(0, scale, result.shape)
            result += noise.astype(np.float32)
        return np.clip(result, -1.0, 1.0)

    def frame_indices(self, total_frames: int, count: int) -> list[int]:
        """Select a sorted subset, useful for frame-drop/temporal sampling variation."""
        if total_frames <= 0 or count <= 0:
            return []
        count = min(total_frames, count)
        return sorted(self.rng.sample(range(total_frames), count))
