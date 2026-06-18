"""Crop a generous full-res face region for isolated donor retouching.

For bodyshots / wide frames the face is small, so a whole-frame generation barely
touches it (and pasting the tiny donor back upscales it → blur). Crop the face out
at full resolution, retouch THAT, then register it back (see ``regions``).

Promoted from the legacy scripts/ surgical toolkit.
"""
from __future__ import annotations

import numpy as np

from .faceparse import FaceGeometry

Box = tuple[int, int, int, int]   # x0, y0, x1, y1


def face_box(geom: FaceGeometry, shape_hw: tuple[int, int], pad: float = 0.6) -> Box:
    """Bounding box of the face oval, padded by ``pad`` x its size, clipped to the frame."""
    h, w = shape_hw
    ys, xs = np.where(geom.face_oval > 0.5)
    if xs.size == 0:
        return (0, 0, w, h)
    x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())
    pw, ph = int(pad * (x1 - x0)), int(pad * (y1 - y0))
    return (max(0, x0 - pw), max(0, y0 - ph), min(w, x1 + pw), min(h, y1 + ph))


def face_crop(rgb: np.ndarray, geom: FaceGeometry, pad: float = 0.6) -> tuple[np.ndarray, Box]:
    """Return (face_crop, box). ``box`` lets the caller paste the retouched crop back."""
    x0, y0, x1, y1 = box = face_box(geom, rgb.shape[:2], pad)
    return rgb[y0:y1, x0:x1].copy(), box
