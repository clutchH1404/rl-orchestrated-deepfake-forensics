"""
Face detection and facial ROI normalization for deepfake visual models.
Optimized for CPU execution with Haar Cascade and fallback central crop.
"""

from pathlib import Path
from typing import List, Tuple, Optional
import numpy as np
from PIL import Image


class FaceDetector:
    """Detects primary facial bounding boxes and extracts normalized 224x224 ROIs."""

    def __init__(self):
        self._cascade = None

    def _get_cascade(self):
        if self._cascade is None:
            try:
                import cv2
                cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                self._cascade = cv2.CascadeClassifier(cascade_path)
            except Exception:
                self._cascade = None
        return self._cascade

    def detect_face_bbox(self, image_np: np.ndarray) -> List[int]:
        """
        Detects primary face bounding box.
        Returns [ymin, xmin, ymax, xmax].
        """
        h, w = image_np.shape[:2]
        cascade = self._get_cascade()

        if cascade is not None:
            try:
                import cv2
                gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY) if len(image_np.shape) == 3 else image_np
                faces = cascade.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=4, minSize=(60, 60)
                )
                if len(faces) > 0:
                    # Pick the largest detected face
                    faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
                    x, y, fw, fh = faces[0]
                    # Add 15% margin for forensic boundary inspection
                    pad_w = int(fw * 0.15)
                    pad_h = int(fh * 0.15)
                    xmin = max(0, x - pad_w)
                    ymin = max(0, y - pad_h)
                    xmax = min(w, x + fw + pad_w)
                    ymax = min(h, y + fh + pad_h)
                    return [int(ymin), int(xmin), int(ymax), int(xmax)]
            except Exception:
                pass

        # Fallback: central crop (assumed portrait / center speaker)
        pad_y = int(h * 0.15)
        pad_x = int(w * 0.20)
        return [pad_y, pad_x, h - pad_y, w - pad_x]

    def extract_face_crop(
        self, image_path: Path, target_size: Tuple[int, int] = (224, 224)
    ) -> Tuple[np.ndarray, List[int]]:
        """
        Extracts and resizes facial crop to target_size.
        Returns (face_rgb_array, bbox).
        """
        with Image.open(image_path) as img:
            rgb_img = img.convert("RGB")
            np_img = np.array(rgb_img)

        bbox = self.detect_face_bbox(np_img)
        ymin, xmin, ymax, xmax = bbox

        face_crop = np_img[ymin:ymax, xmin:xmax]
        if face_crop.size == 0:
            face_crop = np_img

        face_pil = Image.fromarray(face_crop).resize(target_size, Image.Resampling.BILINEAR)
        return np.array(face_pil), bbox
