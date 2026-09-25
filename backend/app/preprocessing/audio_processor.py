"""
Audio preprocessing, spectral analysis, and Mel-spectrogram visualization generator.
Provides forensic features for wav2vec2-base and audio anomaly detection.
"""

from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List
import wave
import struct
import numpy as np
from PIL import Image

from backend.app.core.config import settings
from backend.app.core.logging import log_forensic_event


class AudioProcessor:
    """Extracts raw waveform arrays, computes Mel-scale spectrograms, and renders forensic plots."""

    def __init__(self, audio_path: Path, case_id: str):
        self.audio_path = audio_path
        self.case_id = case_id
        self.artifacts_dir = settings.ARTIFACTS_DIR / case_id
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def load_wav(self) -> Tuple[np.ndarray, int]:
        """Loads WAV audio file into normalized float32 numpy array and sample rate."""
        try:
            with wave.open(str(self.audio_path), "rb") as wf:
                sample_rate = wf.getframerate()
                num_frames = wf.getnframes()
                num_channels = wf.getnchannels()
                raw_data = wf.readframes(num_frames)

                # Format string based on sample width
                if wf.getsampwidth() == 2:
                    dtype = np.int16
                elif wf.getsampwidth() == 4:
                    dtype = np.int32
                else:
                    dtype = np.uint8

                samples = np.frombuffer(raw_data, dtype=dtype).astype(np.float32)

                # If stereo, average down to mono
                if num_channels > 1:
                    samples = samples.reshape(-1, num_channels).mean(axis=1)

                # Normalize to [-1.0, 1.0]
                max_val = np.max(np.abs(samples))
                if max_val > 0:
                    samples = samples / max_val

                return samples, sample_rate
        except Exception as e:
            log_forensic_event(
                event="wav_load_failed",
                case_id=self.case_id,
                details={"error": str(e)},
            )
            raise ValueError(f"Unable to decode WAV audio at {self.audio_path}: {e}") from e

    def compute_spectrogram(
        self,
        samples: np.ndarray,
        sample_rate: int = 16000,
        n_fft: int = 512,
        hop_length: int = 256,
    ) -> np.ndarray:
        """
        Computes power spectrogram using standard Short-Time Fourier Transform (STFT).
        Pure numpy implementation to avoid heavy dynamic C-dependencies on CPU.
        """
        if len(samples) < n_fft:
            samples = np.pad(samples, (0, n_fft - len(samples)))

        window = np.hanning(n_fft)
        num_frames = 1 + (len(samples) - n_fft) // hop_length

        spectrogram = np.empty((n_fft // 2 + 1, num_frames), dtype=np.float32)

        for i in range(num_frames):
            segment = samples[i * hop_length : i * hop_length + n_fft] * window
            fft_result = np.fft.rfft(segment)
            spectrogram[:, i] = np.abs(fft_result) ** 2

        # Convert to logarithmic decibel scale
        spec_db = 10 * np.log10(np.maximum(spectrogram, 1e-10))
        return spec_db

    def render_visualizations(
        self, samples: np.ndarray, spec_db: np.ndarray
    ) -> Tuple[Path, Path]:
        """
        Renders waveform and spectrogram visual artifacts as PNG images.
        Uses pure Pillow color mapping for speed and zero graphical display dependencies.
        Returns (waveform_png_path, spectrogram_png_path).
        """
        # 1. Render Spectrogram PNG
        spec_norm = (spec_db - spec_db.min()) / (spec_db.max() - spec_db.min() + 1e-6)
        spec_uint8 = (spec_norm * 255).astype(np.uint8)

        # Apply viridis/cyan-amber forensic color gradient
        h, w = spec_uint8.shape
        rgb_img = np.zeros((h, w, 3), dtype=np.uint8)
        # Deep blue -> Cyan -> Amber -> White thermal forensic colormap
        rgb_img[:, :, 0] = np.clip(spec_uint8 * 1.5 - 100, 0, 255) # Red
        rgb_img[:, :, 1] = np.clip(spec_uint8 * 1.2, 0, 255) # Green
        rgb_img[:, :, 2] = np.clip(255 - spec_uint8 * 0.8, 0, 255) # Blue

        # Flip vertically so low frequencies are at bottom
        rgb_img = np.flipud(rgb_img)

        spec_pil = Image.fromarray(rgb_img).resize((800, 240), Image.Resampling.BILINEAR)
        spec_path = self.artifacts_dir / "spectrogram.png"
        spec_pil.save(spec_path, "PNG")

        # 2. Render Waveform PNG
        wave_canvas = np.zeros((160, 800, 3), dtype=np.uint8)
        # Dark forensic background #0A101D
        wave_canvas[:, :, 0] = 10
        wave_canvas[:, :, 1] = 16
        wave_canvas[:, :, 2] = 29

        # Downsample waveform to 800 columns
        chunk_size = max(1, len(samples) // 800)
        center_y = 80
        for col in range(min(800, len(samples) // chunk_size)):
            chunk = samples[col * chunk_size : (col + 1) * chunk_size]
            val_min = np.min(chunk)
            val_max = np.max(chunk)
            y1 = int(center_y - val_max * 70)
            y2 = int(center_y - val_min * 70)
            y1 = max(0, min(159, y1))
            y2 = max(0, min(159, y2))
            if y1 > y2:
                y1, y2 = y2, y1
            # Cyan waveform trace #00F0FF
            wave_canvas[y1 : y2 + 1, col, 0] = 0
            wave_canvas[y1 : y2 + 1, col, 1] = 240
            wave_canvas[y1 : y2 + 1, col, 2] = 255

        wave_pil = Image.fromarray(wave_canvas)
        wave_path = self.artifacts_dir / "waveform.png"
        wave_pil.save(wave_path, "PNG")

        return wave_path, spec_path
