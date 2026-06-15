"""P7: golden regression test. Runs the native-resolution audit on the committed,
deterministically-synthesized failure cases and asserts the verdict matches the committed
expectation. Offline (no API). If a change makes the audit stop catching the photo-3 hand
or the photo-2 glasses shadow, or start false-positiving the clean control, this fails."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from retoucher.audit import audit_region

from golden.cases import CASES

_EXPECTED = json.loads((Path(__file__).parent / "golden" / "expected.json").read_text())


def _gate(verdict, name):
    return next(g for g in verdict.gates if g["name"] == name)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.__name__)
def test_golden_verdict_matches_expectation(case):
    base, out, region, skin_ref, name = case()
    v = audit_region(base, out, region, op_id=name, skin_ref=skin_ref)
    exp = _EXPECTED[name]
    assert v.clean is exp["clean"], f"{name}: clean={v.clean}, expected {exp['clean']}"
    for gate_name in exp["must_fail"]:
        assert _gate(v, gate_name)["status"] == "fail", f"{name}: {gate_name} should fail"
