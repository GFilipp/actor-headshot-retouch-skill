# Retouch learnings: the failure log

Every entry is a mistake this project actually shipped, why it happened, and the rule that
now prevents it. Read this before changing the audit, the calibration, or the masks. The
point of the v3 rebuild was to stop relearning these.

## 1. Verifying on interpolated zoom hid every artifact

The single most expensive mistake. A smooth-scaled preview interpolates away boxes, blur,
stipple, and residual marks, so the result looked clean and shipped dirty; a human caught it
every time. **Rule:** the audit runs at nearest-neighbor native resolution
(`audit._assert_native` plus a source-scan test). Never judge on a scaled preview.

## 2. Deterministic-only de-discoloration barely dented real pigment

Pigment is chromatic. The deterministic `reduce_discoloration` nudges a*/b* toward a clean
reference but cannot remove real brown/red the way a regenerate can. **Rule:** pigmentation
and discoloration are generative-led, with deterministic de-discolor as the follow-up, not
the primary (`calibrate.py`).

## 3. Raw paste boxed and dragged color

Pasting donor pixels over sharp or large regions left a rectangular tell, and it dragged the
donor's color (a visible rouge). **Rule:** organic rounded masks with wide feather; on a
large face always color-match to clean skin; otherwise use `luma` (donor luminance, original
chroma) so color cannot drift. The straight `under_eye` hull edge specifically read as a
faint rectangle, so periorbital masks are built as rounded discs off the eyeball.

## 4. The feather faded lashes and brows

A wide feather bled the edit onto the eyelashes and brows. **Rule:** subtract a dilated
protect mask AFTER feathering, in both the composite and the deterministic layers
(`regions.composite_region`, the protect-after-feather step). The `lashes` audit gate checks
that protected-feature edge energy is retained.

## 5. Small / low-resolution faces could not take a paste

On a bodyshot or any small face, pasting regenerated texture distorted badly at pixel zoom;
the fix that worked on a headshot wrecked a small face. **Rule:** `face_px_frac` and
resolution class gate the paste; small or low-resolution faces get a lighter `luma` pass, not
a raw paste (`calibrate.py`, the `large_face_frac` threshold).

## 6. Low-resolution donor crops came back blurry

Cropping a small region (a hand), regenerating it, then upscaling the donor produced a blurry
paste. **Rule:** the `texture` audit gate flags a region whose high-frequency energy falls
below its local skin baseline; the blur escalation switches that region to `transfer` (tone
only, original texture kept) and backs off smoothing.

## 7. Missed marks slipped through because nothing re-scanned the output

A discoloration on the hand and residual marks near the eye survived because the only check
was a human glance. **Rule:** the `residual` audit gate re-runs blemish detection on the
edited region and fails if any pigment or dark candidate is still present. Audit upstream of
the human, not after.

## 8. Ping-ponging between "can't tell you did anything" and "rectangles in my face"

Two failure modes, over-correcting between them. The resolution was the hybrid: let the
generative model carry the real fix (crepe, pigment) and use deterministic follow-ups to
finish, calibrated per region. Neither extreme is the answer.

## 9. Gemini is stochastic

A single generation sometimes came back worse. **Rule:** draw K candidates (`--samples`),
audit each at native resolution, ship the cleanest; if none pass, refuse and report. Never
ship the least-bad.

## 10. The crash that started it all

MediaPipe aborted in the Codex sandbox because the sandbox denies the GPU (Metal). **Rule:**
run locally. `faceparse` sets `MEDIAPIPE_DISABLE_GPU` and probes in a subprocess, but the
real fix is environment, not code.

## Operating constraints (do not relearn these either)

- Never commit Gary's real photos. `inputs/` is gitignored; delivered files live in Google
  Drive (`.../Headshots/20260509 Cisco Shoot/AI Retouched/`).
- Never print or commit the Gemini key (`~/Desktop/gemini.txt`). Paid tier, small budget.
- Use `.venv312/bin/python`. Python 3.12, full deps.
