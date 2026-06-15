"""P3: the Analyze contract — handleable single face, honest refusal otherwise,
and a JSON-serializable assessment/map. Offline via MockAssessor."""
from __future__ import annotations

import json

import numpy as np

from retoucher.analyze import analyze

from _synth import fake_geometry, make_original


class _StubAssessor:
    def __init__(self, payload):
        self.payload = payload

    def assess(self, rgb):
        return self.payload


def test_analyze_single_face_is_handleable_with_map():
    # Inject geometry: the synthetic test image isn't a real MediaPipe-detectable face.
    a, m, geom = analyze(make_original(), geom=fake_geometry())
    assert geom is not None
    assert a.handleable is True and a.face_count == 1
    assert a.shot_type in ("headshot", "three_quarter", "bodyshot")
    assert len(m.ops) > 0                                   # found things to fix
    assert any(o.region == "eye_area" for o in m.ops)
    assert any(s.kind == "face" for s in a.subjects)
    json.dumps(a.to_dict()); json.dumps(m.to_dict())        # report-serializable


def test_analyze_no_face_refuses_not_crashes():
    blank = np.full((400, 400, 3), 0.5, np.float32)
    a, m, geom = analyze(blank)
    assert geom is None
    assert a.handleable is False and "no clear frontal face" in a.reason
    assert "no-face/occluded/profile" in a.out_of_scope


def test_analyze_multi_face_flagged_out_of_scope():
    stub = _StubAssessor({"shot_type": "headshot", "lighting": "soft",
                          "face_count": 2, "defects": []})
    a, m, geom = analyze(make_original(), assessor=stub, geom=fake_geometry())
    assert a.handleable is False
    assert "multi-person" in a.out_of_scope and "2 faces" in a.reason


def test_analyze_out_of_scope_region_flagged_not_mapped():
    stub = _StubAssessor({"shot_type": "headshot", "lighting": "soft", "face_count": 1,
                          "defects": [{"region": "background", "defect": "blemish",
                                       "severity": 0.5, "bbox": [0, 0, 10, 10]}]})
    a, m, geom = analyze(make_original(), assessor=stub, geom=fake_geometry())
    assert "background" in a.out_of_scope
    assert all(o.region != "background" for o in m.ops)     # not silently treated
