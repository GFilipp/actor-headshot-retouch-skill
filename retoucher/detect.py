"""Model-independent blemish / discoloration candidate detection on visible skin.

Finds local redness (LAB a*) and dark-spot anomalies on skin, excluding protected
features, the under-eye, and hair/shadow/blown highlights. Returns structured
``Candidate`` records (not a marked PNG) so they can feed the retouch map AND the
"missed mark" self-audit. Promoted from scripts/detect_blemishes.py.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from skimage.color import rgb2lab

from .faceparse import FaceGeometry
from .image_io import to_uint8
from .mask import skin_mask


@dataclass
class Candidate:
    cx: int
    cy: int
    radius: int
    area: int
    kind: str        # "red" | "dark"
    severity: float  # 0..1


def detect_blemishes(
    rgb: np.ndarray,
    geom: FaceGeometry | None = None,
    *,
    region: np.ndarray | None = None,
    top: int = 8,
    score_thresh: float = 0.6,
) -> list[Candidate]:
    """Detect up to ``top`` candidate blemishes, ranked by severity (mean score x area).

    ``region`` optionally confines the search (e.g. a hand mask from the analyze stage);
    otherwise it searches skin minus protected features / under-eye / hair / highlights.
    """
    rgb = rgb.astype(np.float32)
    h, w = rgb.shape[:2]
    lab = rgb2lab(np.clip(rgb, 0, 1)).astype(np.float32)
    L, a = lab[..., 0], lab[..., 1]

    area_mask = skin_mask(rgb) if region is None else np.clip(region, 0, 1)
    if geom is not None and region is None:
        protect = cv2.dilate(geom.protect, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25)))
        area_mask = area_mask * (1.0 - np.clip(protect + geom.under_eye, 0, 1))
    area_mask = area_mask * ((L > 25) & (L < 92)).astype(np.float32)   # drop hair/shadow/highlight

    red = np.clip(a - cv2.GaussianBlur(a, (0, 0), 30), 0, None)
    dark = np.clip(cv2.GaussianBlur(L, (0, 0), 30) - L, 0, None)
    red_s = red / 6.0
    dark_s = dark / 12.0
    score = np.maximum(red_s, dark_s) * (area_mask > 0.5)

    cand = (score > score_thresh).astype(np.uint8)
    n, labels, stats, cent = cv2.connectedComponentsWithStats(cand, 8)
    out: list[Candidate] = []
    for i in range(1, n):
        area = int(stats[i, cv2.CC_STAT_AREA])
        if not (8 <= area <= 1800):
            continue
        sel = labels == i
        cx, cy = int(cent[i][0]), int(cent[i][1])
        kind = "red" if red_s[sel].mean() >= dark_s[sel].mean() else "dark"
        sev = float(score[sel].mean())
        out.append(Candidate(cx, cy, max(8, int(1.6 * (area / 3.14159) ** 0.5)), area, kind, sev))
    out.sort(key=lambda c: -c.severity * c.area)
    return out[:top]
