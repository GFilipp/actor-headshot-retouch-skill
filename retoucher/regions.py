"""Surgical region compositing — register a generated *donor* onto the original
and composite ONE organic region back, in one of three calibrated modes.

    paste     donor pixels (carries texture/crepe fix; boxes on sharp/large regions
              and drags the donor's colour) -> large/high-res faces, targeted
    transfer  donor's LOW-FREQUENCY tone/darkness delta only; original texture kept
              (seamless, no box, no crepe) -> tone/discoloration without texture risk
    luma      donor LUMINANCE (carries the crepe/structure fix) but ORIGINAL colour
              (no colour distortion) -> crepe fix on colour-sensitive / small faces

Two hard rules learned the hard way and enforced here:
- region masks are ORGANIC (rounded, wide-feathered) — a straight mask edge leaves a
  faint rectangular tell at any strength;
- features (brows/eyes/lips/lashes) are re-protected AFTER feathering, so the feather
  can't bleed an edit onto them.

Promoted from scripts/surgical_paste.py.
"""
from __future__ import annotations

import cv2
import numpy as np
from skimage.color import lab2rgb, rgb2lab

from .align import align_to_reference
from .faceparse import FaceGeometry, landmarks
from .image_io import clip01

MODES = ("paste", "transfer", "luma")


def _kernel(px: float) -> np.ndarray:
    r = max(1, int(round(px)))
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (r * 2 + 1, r * 2 + 1))


def _dilate(m: np.ndarray, px: float) -> np.ndarray:
    return cv2.dilate(m.astype(np.float32), _kernel(px))


def _feather(m: np.ndarray, sigma: float) -> np.ndarray:
    return cv2.GaussianBlur(m.astype(np.float32), (0, 0), sigmaX=max(1.0, sigma))


def build_region(geom: FaceGeometry, name: str, grow: float = 1.0) -> np.ndarray:
    """Organic face-region mask (float 0/1). Rounded discs only — never the straight
    ``under_eye`` hull on its own — so the composite leaves no rectangular tell."""
    if name == "face":
        return geom.face_oval.astype(np.float32)
    if name == "under_eye":
        return geom.under_eye.astype(np.float32)
    if name == "periorbital":
        ys = np.where(geom.eyes.max(axis=1) > 0.5)[0]
        eye_h = float(ys.max() - ys.min()) if ys.size else 0.08 * geom.eyes.shape[0]
        disc = _dilate(geom.eyes, grow * eye_h)                       # rounded — no straight edges
        return np.clip(disc * (1.0 - geom.eyes) * geom.face_oval, 0, 1)
    raise ValueError(f"unknown region {name!r}; expected face|under_eye|periorbital")


def color_match(src: np.ndarray, ref: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Shift src's per-channel LAB mean to ref's over ``mask`` — neutralises a global
    colour/brightness difference (e.g. a donor's added warmth) while keeping detail."""
    sel = mask > 0.5
    if int(sel.sum()) < 50:
        return src
    s = rgb2lab(clip01(src)).astype(np.float32)
    r = rgb2lab(clip01(ref)).astype(np.float32)
    for c in range(3):
        s[..., c] += float(r[..., c][sel].mean() - s[..., c][sel].mean())
    return clip01(lab2rgb(s)).astype(np.float32)


def register_donor(original: np.ndarray, donor: np.ndarray) -> tuple[np.ndarray, str, float]:
    """Register ``donor`` onto ``original``'s grid. Prefers a face-landmark affine
    (works when both have a detectable face); falls back to ECC/ORB intensity
    registration (``align.align_to_reference``) for non-face regions (hands/neck).

    Returns (aligned_donor, method, score) where score in [0,1] (1 = best/identity)."""
    h, w = original.shape[:2]
    donor = cv2.resize(donor.astype(np.float32), (w, h)) if donor.shape[:2] != (h, w) else donor.astype(np.float32)
    lo, ld = landmarks(original), landmarks(donor)
    if lo is not None and ld is not None:
        m, inliers = cv2.estimateAffinePartial2D(ld, lo, method=cv2.RANSAC)
        if m is not None:
            warped = cv2.warpAffine(donor, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            score = float(np.mean(inliers)) if inliers is not None else 1.0
            return clip01(warped), "landmark-affine", score
    al = align_to_reference(original, donor)              # ECC -> ORB -> identity
    return clip01(al.warped), al.method, float(al.score)


def composite_region(
    original: np.ndarray,
    donor: np.ndarray,
    region: np.ndarray,
    *,
    mode: str = "luma",
    strength: float = 1.0,
    feather: float | None = None,
    protect: np.ndarray | None = None,
    transfer_sigma: float | None = None,
) -> np.ndarray:
    """Composite the (already registered) ``donor`` into ``region`` of ``original``.

    ``region`` is a float mask; it is feathered here and the protected features are
    subtracted AFTER feathering so nothing bleeds onto brows/eyes/lips/lashes.
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, got {mode!r}")
    original = original.astype(np.float32)
    donor = donor.astype(np.float32)
    h, w = original.shape[:2]
    feather = feather if feather is not None else max(4.0, 0.01 * max(h, w))

    m = _feather(np.clip(region, 0, 1), feather) * float(strength)
    if protect is not None:
        prot = _feather(_dilate(protect, max(2.0, feather * 0.4)), feather * 0.4)
        m = m * (1.0 - np.clip(prot, 0, 1))
    m3 = m[..., None]

    if mode == "paste":
        out = original * (1 - m3) + donor * m3
    elif mode == "transfer":
        s = transfer_sigma or max(8.0, 0.006 * max(h, w))
        delta = cv2.GaussianBlur(donor, (0, 0), sigmaX=s) - cv2.GaussianBlur(original, (0, 0), sigmaX=s)
        out = original + m3 * delta                       # donor's tone/darkness; original texture kept
    else:  # luma
        lab_o = rgb2lab(clip01(original)).astype(np.float32)
        lab_d = rgb2lab(clip01(donor)).astype(np.float32)
        lab_o[..., 0] = lab_o[..., 0] * (1 - m) + lab_d[..., 0] * m   # donor luminance only
        out = lab2rgb(lab_o)
    return clip01(out).astype(np.float32)
