"""P4: the Calibrate contract — the rulebook, asserted clause by clause. Pure policy,
no image data needed; we construct assessments and ops directly."""
from __future__ import annotations

import copy

from retoucher.calibrate import (
    DET_DISCOLOR, DET_EVEN, DET_HEAL, DET_SMOOTH, DET_WHITEN, calibrate, escalate,
)
from retoucher.schema import PhotoAssessment, RegionVerdict, RetouchMap, RetouchOp

BIG = PhotoAssessment(shot_type="headshot", face_px_frac=0.12, resolution_class="native_high",
                      face_count=1, handleable=True)
SMALL = PhotoAssessment(shot_type="bodyshot", face_px_frac=0.01, resolution_class="native_low",
                        face_count=1, handleable=True)


def _op(defect, *, region="face", sev=0.6, bbox=(10, 10, 60, 50), identity=False):
    return RetouchOp(op_id=f"op-{defect}", region=region, defect=defect, severity=sev,
                     bbox=bbox, identity_sensitive=identity)


def _one(op, assessment=BIG, cfg=None):
    return calibrate(assessment, RetouchMap(ops=[op]), cfg)[0]


def test_one_record_per_op_ids_preserved():
    m = RetouchMap(ops=[_op("under_eye", region="eye_area"), _op("blemish"), _op("flyaway", region="hair")])
    recs = calibrate(BIG, m)
    assert [r.op_id for r in recs] == [o.op_id for o in m.ops]


def test_flyaway_is_generative_only():
    r = _one(_op("flyaway", region="hair"))
    assert r.gen_weight == 1.0 and r.composite_mode == "paste" and r.det_ops == []


def test_eye_white_cast_is_deterministic_only():
    r = _one(_op("eye_white_cast", region="eye_area"))
    assert r.gen_weight == 0.0 and r.composite_mode == "none"
    assert r.det_ops == [DET_WHITEN] and r.mask_kind == "eyes"


def test_pigmentation_is_generative_led_with_discolor_followup():
    r = _one(_op("pigmentation"))
    assert r.gen_weight > 0 and DET_DISCOLOR in r.det_ops
    assert "chromatic" in r.rationale


def test_small_face_never_raw_pastes():
    # The exact illusion that bit us: a raw paste on a small/low-res face.
    for defect in ("pigmentation", "discoloration", "under_eye", "crepe"):
        r = _one(_op(defect, region="eye_area"), assessment=SMALL)
        assert r.composite_mode != "paste", defect
        assert r.composite_mode == "luma", defect


def test_big_face_pastes_under_eye_with_smooth_and_discolor():
    r = _one(_op("under_eye", region="eye_area"))
    assert r.composite_mode == "paste" and r.gen_weight >= 0.8
    assert r.det_ops == [DET_SMOOTH, DET_DISCOLOR]


def test_mild_unevenness_is_deterministic_only_strong_is_generative():
    mild = _one(_op("skin_unevenness", sev=0.3))
    assert mild.gen_weight == 0.0 and mild.det_ops == [DET_EVEN]
    strong = _one(_op("skin_unevenness", sev=0.8))
    assert strong.gen_weight > 0 and DET_EVEN in strong.det_ops


def test_blemish_is_targeted_deterministic_heal():
    r = _one(_op("blemish"))
    assert r.gen_weight == 0.0 and r.det_ops == [DET_HEAL]


def test_identity_sensitive_caps_gen_and_downgrades_paste():
    base = _one(_op("under_eye", region="eye_area", identity=False))
    capped = _one(_op("under_eye", region="eye_area", identity=True))
    assert base.composite_mode == "paste" and base.gen_weight > 0.5
    assert capped.gen_weight <= 0.5 and capped.composite_mode == "luma"
    assert "identity-sensitive" in capped.rationale


def test_det_strength_scales_with_severity():
    lo = _one(_op("pigmentation", sev=0.2)).strength[DET_DISCOLOR]
    hi = _one(_op("pigmentation", sev=0.9)).strength[DET_DISCOLOR]
    assert hi > lo


def test_feather_derived_from_bbox_and_positive():
    small_box = _one(_op("blemish", bbox=(0, 0, 20, 20)))
    big_box = _one(_op("blemish", bbox=(0, 0, 400, 400)))
    assert small_box.feather_px > 0 and big_box.feather_px > small_box.feather_px


def test_hands_use_ecc_patch_mask():
    r = _one(_op("discoloration", region="hands"))
    assert r.mask_kind == "ecc_patch"


def test_pure_no_mutation_and_deterministic():
    m = RetouchMap(ops=[_op("under_eye", region="eye_area"), _op("pigmentation", region="hands")])
    before = copy.deepcopy(m)
    r1 = [r.to_dict() for r in calibrate(BIG, m)]
    r2 = [r.to_dict() for r in calibrate(BIG, m)]
    assert r1 == r2                                       # deterministic
    assert [o.__dict__ for o in m.ops] == [o.__dict__ for o in before.ops]  # no mutation


# ---- escalate (audit-driven re-calibration) ----------------------------------------

def _verdict(*fails):
    gates = [{"name": n, "status": "fail", "value": 1.0, "threshold": 0.0,
              "detail": d, "required": True} for n, d in fails]
    return RegionVerdict(op_id="op", clean=False, gates=gates)


def test_escalate_noop_when_clean():
    rec = _one(_op("under_eye", region="eye_area"))
    clean = RegionVerdict(op_id="op", clean=True, gates=[
        {"name": "seam", "status": "pass", "value": 0.0, "threshold": 0.0, "detail": "", "required": True}])
    assert escalate(rec, clean) == rec


def test_escalate_seam_widens_feather_and_grow():
    rec = _one(_op("under_eye", region="eye_area"))
    esc = escalate(rec, _verdict(("seam", "hard edge / box")))
    assert esc.feather_px > rec.feather_px and esc.grow > rec.grow


def test_escalate_blur_switches_to_transfer_and_lowers_gen():
    rec = _one(_op("under_eye", region="eye_area"))           # paste, high gen
    esc = escalate(rec, _verdict(("texture", "blur / plastic: texture below local skin")))
    assert esc.composite_mode == "transfer" and esc.gen_weight < rec.gen_weight


def test_escalate_residual_forces_max_discolor_and_heal():
    rec = _one(_op("under_eye", region="eye_area"))
    esc = escalate(rec, _verdict(("residual", "pigment/dark mark still present")))
    assert DET_DISCOLOR in esc.det_ops and DET_HEAL in esc.det_ops
    assert esc.strength[DET_DISCOLOR] >= rec.strength.get(DET_DISCOLOR, 0)


def test_escalate_color_caps_generative_share():
    rec = _one(_op("under_eye", region="eye_area"))           # gen ~0.8
    esc = escalate(rec, _verdict(("color", "color cast / rouge")))
    assert esc.gen_weight <= 0.6 and DET_DISCOLOR in esc.det_ops
