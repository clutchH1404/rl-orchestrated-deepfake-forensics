"""
Media extraction and metadata forensic analysis.
Extracts video frames, audio tracks, and technical container properties.
Preserves original media; works entirely on isolated forensic working copies.
"""

import subprocess
import json
import mimetypes
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from PIL import Image

from backend.app.core.config import settings
from backend.app.core.logging import log_forensic_event
from backend.app.schemas.case import MediaMetadata


def get_ffmpeg_binary() -> Optional[str]:
    """Retrieves ffmpeg executable path from imageio_ffmpeg or system PATH."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        # Check standard system PATH
        return "ffmpeg"


class MediaExtractor:
    """Extracts forensic metadata, keyframes, and separated audio tracks."""

    def __init__(self, working_copy_path: Path, case_id: str):
        self.path = working_copy_path
        self.case_id = case_id
        self.artifacts_dir = settings.ARTIFACTS_DIR / case_id
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.frames_dir = self.artifacts_dir / "frames"
        self.frames_dir.mkdir(parents=True, exist_ok=True)

    def determine_modality(self, extension: str) -> str:
        ext = extension.lower().strip(".")
        if ext in ["mp4", "mov", "avi", "mkv"]:
            return "video"
        elif ext in ["wav", "mp3", "flac", "m4a"]:
            return "audio"
        elif ext in ["jpg", "jpeg", "png", "webp"]:
            return "image"
        return "unknown"

    def extract_metadata(
        self, original_sha256: str, processed_sha256: str
    ) -> MediaMetadata:
        """Extracts container metadata and hardware-verifiable technical properties."""
        file_size = self.path.stat().st_size
        extension = self.path.suffix.lower().strip(".")
        modality = self.determine_modality(extension)

        duration: Optional[float] = None
        resolution: Optional[str] = None
        fps: Optional[float] = None
        has_video = modality in ["video", "image"]
        has_audio = modality in ["video", "audio"]
        sample_rate: Optional[int] = None
        channels: Optional[int] = None
        extra_meta: Dict[str, Any] = {}

        if modality == "image":
            try:
                with Image.open(self.path) as img:
                    resolution = f"{img.width}x{img.height}"
                    extra_meta["format"] = img.format
                    extra_meta["mode"] = img.mode
            except Exception as e:
                extra_meta["image_read_error"] = str(e)

        elif modality == "video":
            # Attempt extraction via cv2 or ffprobe
            try:
                import cv2
                cap = cv2.VideoCapture(str(self.path))
                if cap.isOpened():
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps_val = float(cap.get(cv2.CAP_PROP_FPS))
                    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    resolution = f"{width}x{height}"
                    fps = round(fps_val, 2) if fps_val > 0 else 30.0
                    duration = round(frame_count / fps, 2) if fps > 0 else 0.0
                    extra_meta["frame_count"] = frame_count
                    cap.release()
            except Exception as e:
                extra_meta["video_probe_error"] = str(e)
                # Technical values are unknown when probing fails; do not invent defaults.

        elif modality == "audio":
            try:
                import wave
                with wave.open(str(self.path), "rb") as audio:
                    sample_rate = audio.getframerate()
                    channels = audio.getnchannels()
                    duration = round(audio.getnframes() / sample_rate, 3) if sample_rate else None
            except Exception as e:
                extra_meta["audio_probe_error"] = str(e)

        mime_type = mimetypes.guess_type(self.path.name)[0] or "application/octet-stream"

        return MediaMetadata(
            filename=self.path.name,
            original_sha256=original_sha256,
            processed_sha256=processed_sha256,
            file_size_bytes=file_size,
            mime_type=mime_type,
            modality_type=modality,
            duration_seconds=duration,
            resolution=resolution,
            fps=fps,
            audio_sample_rate=sample_rate,
            audio_channels=channels,
            has_video=has_video,
            has_audio=has_audio,
            extra_metadata=extra_meta,
        )

    def extract_keyframes(self, num_frames: int = 16) -> List[Tuple[int, float, Path]]:
        """
        Extracts strategic keyframes uniformly distributed across the video timeline.
        Returns list of (frame_index, timestamp_seconds, frame_file_path).
        """
        modality = self.determine_modality(self.path.suffix)
        extracted: List[Tuple[int, float, Path]] = []

        if modality == "image":
            # For static images, single frame at t=0
            target_path = self.frames_dir / "frame_0000.png"
            with Image.open(self.path) as img:
                img.convert("RGB").save(target_path, "PNG")
            return [(0, 0.0, target_path)]

        if modality != "video":
            return []

        try:
            import cv2
            cap = cv2.VideoCapture(str(self.path))
            if not cap.isOpened():
                return []

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = float(cap.get(cv2.CAP_PROP_FPS)) or 30.0

            if total_frames <= 0:
                total_frames = num_frames

            # Calculate uniform step
            indices = [int(i * (total_frames - 1) / max(1, num_frames - 1)) for i in range(num_frames)]

            for idx in indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if ret and frame is not None:
                    timestamp = round(idx / fps, 3)
                    frame_path = self.frames_dir / f"frame_{idx:05d}.jpg"
                    cv2.imwrite(str(frame_path), frame)
                    extracted.append((idx, timestamp, frame_path))

            cap.release()
        except Exception as e:
            log_forensic_event(
                event="keyframe_extraction_error",
                case_id=self.case_id,
                details={"error": str(e)},
            )

        return extracted

    def extract_audio_track(self) -> Optional[Path]:
        """
        Extracts the audio track into a normalized 16kHz mono WAV file for wav2vec2.
        Uses imageio_ffmpeg or subprocess ffmpeg.
        """
        modality = self.determine_modality(self.path.suffix)
        if modality not in ["video", "audio"]:
            return None

        audio_output_path = self.artifacts_dir / "extracted_audio_16k.wav"

        ffmpeg_exe = get_ffmpeg_binary()
        if not ffmpeg_exe:
            return None

        # Build ffmpeg conversion command: extract audio, 16kHz, mono, 16-bit PCM WAV
        cmd = [
            ffmpeg_exe,
            "-y", # Overwrite
            "-i", str(self.path),
            "-vn", # Disable video recording
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            str(audio_output_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                check=False,
            )
            if audio_output_path.exists() and audio_output_path.stat().st_size > 0:
                log_forensic_event(
                    event="audio_track_extracted",
                    case_id=self.case_id,
                    details={"path": str(audio_output_path), "size_bytes": audio_output_path.stat().st_size},
                )
                return audio_output_path
        except Exception as e:
            log_forensic_event(
                event="audio_extraction_failed",
                case_id=self.case_id,
                details={"error": str(e)},
            )

        return None
