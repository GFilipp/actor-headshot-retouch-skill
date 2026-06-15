"""P1: deterministic eye polish runs, eases the eye area, and never touches brows."""
from __future__ import annotations

import numpy as np

from retoucher.cleanup import polish_eyes

from _synth import fake_geometry, make_original


def test_polish_eases_eye_area_and_protects_brows():
    orig = make_original()
    g = fake_geometry()
    out = polish_eyes(orig, g, whites=0.7, discolor=0.6, lines=0.3)

    assert out.shape == orig.shape
    # brows are protected (re-applied after feather) -> essentially unchanged
    brows = g.brows > 0.5
    assert float(np.abs(out[brows] - orig[brows]).mean()) < 0.04
    # the under-eye area IS worked
    ue = g.under_eye > 0.5
    assert float(np.abs(out[ue] - orig[ue]).mean()) > 1e-4


def test_polish_zero_strength_is_noop():
    orig = make_original()
    g = fake_geometry()
    out = polish_eyes(orig, g, whites=0.0, discolor=0.0, lines=0.0)
    assert float(np.abs(out - orig).max()) < 1e-4
