"""Deterministic image fingerprints and comparison measures for source retrieval."""

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class ImageFingerprint:
    ahash: str
    dhash: str
    phash: str
    width: int
    height: int


def _bits_to_hex(bits: np.ndarray) -> str:
    return f"{int(''.join('1' if bit else '0' for bit in bits.ravel()), 2):0{len(bits.ravel()) // 4}x}"


def _grayscale(path: Path, size: tuple[int, int]) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("L").resize(size, Image.Resampling.LANCZOS), dtype=np.float32)


def fingerprint(path: Path) -> ImageFingerprint:
    """Return standard average, difference, and DCT perceptual hashes."""
    with Image.open(path) as image:
        width, height = image.size
    a = _grayscale(path, (8, 8))
    ahash = _bits_to_hex(a >= a.mean())
    d = _grayscale(path, (9, 8))
    dhash = _bits_to_hex(d[:, 1:] >= d[:, :-1])
    try:
        from scipy.fft import dctn
        coefficients = dctn(_grayscale(path, (32, 32)), type=2, norm="ortho")[:8, :8]
        median = np.median(coefficients.ravel()[1:])
        phash = _bits_to_hex(coefficients >= median)
    except ImportError as exc:
        raise RuntimeError("pHash requires scipy; install the declared backend dependency.") from exc
    return ImageFingerprint(ahash=ahash, dhash=dhash, phash=phash, width=width, height=height)


def hamming_distance(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def structural_similarity(query: Path, candidate: Path) -> float:
    """Global SSIM on normalized grayscale thumbnails, bounded to [0, 1]."""
    x, y = _grayscale(query, (256, 256)) / 255.0, _grayscale(candidate, (256, 256)) / 255.0
    mean_x, mean_y, var_x, var_y = x.mean(), y.mean(), x.var(), y.var()
    covariance = ((x - mean_x) * (y - mean_y)).mean()
    score = ((2 * mean_x * mean_y + 0.01**2) * (2 * covariance + 0.03**2)) / ((mean_x**2 + mean_y**2 + 0.01**2) * (var_x + var_y + 0.03**2))
    return float(np.clip(score, 0.0, 1.0))


def crop_similarity(query: Path, candidate: Path) -> float:
    """Compare center crops; a proxy, not evidence of image derivation."""
    def crop(path: Path) -> np.ndarray:
        image = _grayscale(path, (256, 256)) / 255.0
        return image[64:192, 64:192]
    return float(np.clip(1.0 - np.mean(np.abs(crop(query) - crop(candidate))), 0.0, 1.0))
