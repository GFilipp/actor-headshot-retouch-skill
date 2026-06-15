"""Deterministic 'Photoshop' polish — Layer 2, applied after the surgical paste.

Whitens the sclera, eases the red/brown discoloration ring around the eye (toward
CLEAN reference skin, reaching the rim), and softens residual fine lines. Uses an
organic rounded eye-area mask and re-protects features so nothing fades the lashes.
Keep it tasteful — the generative paste does the heavy lifting.

Promoted from scripts/polish_eyes.py.
"""
from __future__ import annotations

import numpy as np

from .blend import reduce_discoloration, smooth_under_eye_texture, whiten_eye_whites
from .faceparse import FaceGeometry
from .regions import _dilate, _feather


def polish_eyes(
    rgb: np.ndarray,
    geom: FaceGeometry,
    *,
    whites: float = 0.6,
    discolor: float = 0.5,
    lines: float = 0.25,
    reference_dim: int = 1024,
) -> np.ndarray:
    """Apply the eye-area polish. Strengths are 0..1; all ops are feature-protected."""
    res = rgb.astype(np.float32)
    h, w = res.shape[:2]
    spatial = max(h, w) / float(reference_dim)
    sigma = 8.0 * spatial

    ys = np.where(geom.eyes.max(axis=1) > 0.5)[0]
    eye_h = float(ys.max() - ys.min()) if ys.size else 0.08 * h
    area = _dilate(geom.eyes, 1.0 * eye_h) * geom.face_oval          # rounded disc, no straight edges
    protect_wide = _dilate(geom.protect, max(2.0, 4.0 * spatial))    # SMOOTHING: keep off lashes
    protect_tight = _dilate(geom.protect, max(1.0, 1.0 * spatial))   # DISCOLOR: reach the rim
    ref = np.clip(geom.face_oval - area - protect_wide, 0.0, 1.0)    # clean cheek/forehead skin

    res = whiten_eye_whites(res, geom.eyes, whites)
    disc = _feather(area * (1.0 - _feather(protect_tight, sigma * 0.3)), sigma * 0.6)
    res = reduce_discoloration(res, disc, discolor, ref)
    soft = _feather(area, max(60.0, 0.6 * eye_h)) * (1.0 - _feather(protect_wide, sigma * 0.5))
    res = smooth_under_eye_texture(res, soft, lines, sigma, protect=protect_wide)
    return res
