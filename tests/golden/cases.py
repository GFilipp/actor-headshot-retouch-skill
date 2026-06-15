"""Golden cases: the named real-world failures from this project, synthesized
deterministically.

Gary's real photos must never enter the repo (`inputs/` is gitignored; deliveries live in
Google Drive), so the golden set reproduces the failure SIGNATURES rather than the photos:
the photo-3 hand (a low-res blurry paste with a missed mark), the photo-2 glasses shadow (a
hard-edged dark paste), and a clean control (a proper feathered edit) to prove the audit
does not false-positive. Deterministic and offline, so CI fails on any audit regression.
"""
from __future__ import annotations

import cv2
import numpy as np

from retoucher.mask import _feather

H = W = 256


def _skin(seed: int) -> np.ndarray:
    rng = np.random.RandomState(seed)
    base = np.full((H, W, 3), np.array([0.80, 0.66, 0.56], np.float32), np.float32)
    base += rng.normal(0, 0.012, (H, W, 3)).astype(np.float32)
    return np.clip(base, 0, 1)


def _disc(cy, cx, r) -> np.ndarray:
    yy, xx = np.ogrid[:H, :W]
    return ((yy - cy) ** 2 + (xx - cx) ** 2 <= r * r).astype(np.float32)


_REF = _disc(40, 40, 22)


def photo3_hand_blur_and_missed_mark():
    """The open bug, folded in as a golden: a low-res donor pasted back blurry AND a
    pigment mark left behind. The audit MUST flag it (texture blur + residual)."""
    base = _skin(1)
    region = _disc(128, 128, 55)
    out = base.copy()
    m = region > 0.5
    out[m] = cv2.GaussianBlur(base, (0, 0), 4)[m]              # blurry upscaled donor
    out[_disc(128, 152, 6) > 0.5] = np.array([0.45, 0.16, 0.16], np.float32)   # missed mark
    return base, out, region, _REF, "photo3_hand_blur_and_missed_mark"


def photo2_glasses_hard_shadow():
    """Photo 2's failure: a hard-edged paste behind glasses left a shadow/seam. The audit
    MUST flag the boundary (seam)."""
    base = _skin(2)
    region = _disc(112, 128, 40)
    out = base.copy()
    m = region > 0.5
    out[m] = np.clip(base[m] - 0.18, 0, 1)                    # hard dark block, no feather
    return base, out, region, _REF, "photo2_glasses_hard_shadow"


def clean_feathered_edit():
    """Control: a proper organic, feathered, color-faithful edit. The audit must pass it,
    so we know the gates do not false-positive on good work."""
    base = _skin(3)
    region = _disc(128, 128, 55)
    fm = _feather(region, 14.0)[..., None]
    out = np.clip(base * (1 - fm) + np.clip(base + 0.05, 0, 1) * fm, 0, 1)
    return base, out, region, _REF, "clean_feathered_edit"


CASES = [photo3_hand_blur_and_missed_mark, photo2_glasses_hard_shadow, clean_feathered_edit]
