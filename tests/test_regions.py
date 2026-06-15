"""P1: surgical region compositing — each mode moves the right band; features safe."""
from __future__ import annotations

import cv2
import numpy as np
import pytest
from skimage.color import lab2rgb, rgb2lab

from retoucher.demo import H, W
from retoucher.regions import build_region, color_match, composite_region, register_donor

from _synth import disk, fake_geometry, make_original


def _disk_mask(cy, cx, r):
    m = np.zeros((H, W), np.float32)
    m[disk(cy, cx, r)] = 1.0
    return m


def _gray(x):
    return x @ np.array([0.299, 0.587, 0.114], np.float32)


def test_paste_replaces_in_core_keeps_outside():
    orig = make_original()
    donor = np.zeros_like(orig) + np.array([0.2, 0.4, 0.6], np.float32)
    out = composite_region(orig, donor, _disk_mask(128, 128, 45), mode="paste", feather=4)
    assert np.abs(out[disk(128, 128, 20)] - donor[disk(128, 128, 20)]).mean() < 0.05  # core == donor
    assert np.abs(out[disk(8, 8, 4)] - orig[disk(8, 8, 4)]).max() < 1e-3              # outside == original


def test_transfer_preserves_texture():
    orig = make_original()
    donor = np.clip(cv2.GaussianBlur(orig, (0, 0), 8) * 0.95 + 0.03, 0, 1)   # low-freq only + tone shift
    out = composite_region(orig, donor, _disk_mask(128, 128, 50), mode="transfer", feather=6)

    def hf(x, sel):
        g = _gray(x)
        return float(np.abs(g - cv2.GaussianBlur(g, (0, 0), 2))[sel].mean())

    core = disk(128, 128, 25)
    assert hf(out, core) > 0.5 * hf(orig, core)        # original texture largely kept
    assert hf(out, core) > 3 * hf(donor, core)         # not the donor's washed-out texture


def test_luma_keeps_original_chroma_moves_luminance():
    orig = make_original()
    lab = rgb2lab(np.clip(orig, 0, 1)).astype(np.float32)
    lab[..., 1] += 15.0                                 # shift donor chroma (a*)
    lab[..., 0] = np.clip(lab[..., 0] + 12.0, 0, 100)   # and luminance
    donor = np.clip(lab2rgb(lab), 0, 1).astype(np.float32)
    out = composite_region(orig, donor, _disk_mask(128, 128, 50), mode="luma", feather=6)

    core = disk(128, 128, 22)
    a_o = rgb2lab(np.clip(orig, 0, 1))[..., 1][core]
    a_out = rgb2lab(np.clip(out, 0, 1))[..., 1][core]
    L_o = rgb2lab(np.clip(orig, 0, 1))[..., 0][core]
    L_out = rgb2lab(np.clip(out, 0, 1))[..., 0][core]
    assert float(np.abs(a_out - a_o).mean()) < 1.5      # chroma stays the original's (no colour shift)
    assert float(L_out.mean() - L_o.mean()) > 3.0       # luminance moved toward the donor


def test_color_match_pulls_mean_toward_reference():
    orig = make_original()
    tinted = np.clip(orig + np.array([0.10, -0.02, -0.05], np.float32), 0, 1)
    matched = color_match(tinted, orig, np.ones((H, W), np.float32))
    before = np.abs(tinted.mean((0, 1)) - orig.mean((0, 1))).max()
    after = np.abs(matched.mean((0, 1)) - orig.mean((0, 1))).max()
    assert after < before * 0.25


def test_build_region_periorbital_is_organic_and_off_eyeball():
    g = fake_geometry()
    peri = build_region(g, "periorbital", grow=0.8)
    assert peri.shape == (H, W)
    assert float((peri * g.eyes).max()) < 0.2          # excludes the eyeball
    assert float((peri * (1 - g.face_oval)).max()) < 0.3   # stays ~within the face
    with pytest.raises(ValueError):
        build_region(g, "nose")


def test_register_donor_returns_aligned_same_shape():
    orig = make_original()
    donor = cv2.resize(orig, (W // 2, H // 2))          # different size on purpose
    out, method, score = register_donor(orig, donor)
    assert out.shape == orig.shape
    assert isinstance(method, str) and 0.0 <= score <= 1.0001
