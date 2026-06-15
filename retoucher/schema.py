"""Typed contracts that flow through the v3 system and land in the JSON report, so
every decision (what was found, how it was treated, the verdict) is auditable and
replayable. Plain dataclasses; all `to_dict()`-able.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

Box = tuple[int, int, int, int]   # x0, y0, x1, y1

# In-scope regions for this build (Gary-locked). Anything else gets an explicit
# out_of_scope flag in the assessment — never a silent skip.
IN_SCOPE_REGIONS = ("face", "eye_area", "neck", "chest", "hands", "hair")
DEFECTS = (
    "under_eye", "crepe", "pigmentation", "discoloration", "blemish",
    "skin_unevenness", "eye_white_cast", "flyaway",
)


@dataclass
class Subject:
    kind: str                 # face | hands | neck | chest | hair
    bbox: Box
    px_area_frac: float
    landmarks_available: bool = False


@dataclass
class PhotoAssessment:
    """What the photo IS + whether/how we can treat it (Analyze contract)."""
    shot_type: str            # headshot | three_quarter | bodyshot | unknown
    face_px_frac: float       # face-oval area / frame — the paste-vs-light pivot
    resolution_class: str     # native_high | native_low | upscaled
    face_count: int
    handleable: bool          # False -> refuse/flag (multi-face, profile, no-face, occluded)
    reason: str = ""          # why not handleable, or notes
    lighting: str = "unknown"
    subjects: list[Subject] = field(default_factory=list)
    skin_refs: dict[str, Box] = field(default_factory=dict)   # region -> clean-skin patch bbox
    out_of_scope: list[str] = field(default_factory=list)     # explicit "not treated" flags

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RetouchOp:
    """One thing to fix (RetouchMap contract)."""
    op_id: str
    region: str
    defect: str
    severity: float           # 0..1
    bbox: Box
    identity_sensitive: bool = False
    source: str = "cv"        # vlm | cv | both


@dataclass
class RetouchMap:
    ops: list[RetouchOp] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"ops": [asdict(o) for o in self.ops]}


@dataclass
class CalibrationRecord:
    """How to fix one op (Calibrate contract) — a decided split, with the reason."""
    op_id: str
    gen_weight: float                 # 0..1 share from the regenerated paste
    composite_mode: str               # paste | transfer | luma | none
    det_ops: list[str] = field(default_factory=list)   # deterministic follow-ups
    mask_kind: str = ""
    grow: float = 1.0
    feather_px: float = 0.0
    strength: dict[str, float] = field(default_factory=dict)
    rationale: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RegionVerdict:
    """Per-region audit result (Verdict contract)."""
    op_id: str
    clean: bool
    gates: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"op_id": self.op_id, "clean": self.clean, "gates": self.gates}
