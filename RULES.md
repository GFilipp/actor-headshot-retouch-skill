# Pre-delivery rules

A short, blunt checklist. The system enforces most of these in code; this is the human
backstop and the place to look when something ships wrong. Do not skip a line.

## Before editing

- [ ] Run locally, not in a sandboxed environment. It denies the GPU and MediaPipe aborts.
- [ ] Use `.venv312/bin/python` (full deps: mediapipe, opencv-contrib, google-genai).
- [ ] Confirm the input is a single, frontal, in-scope photo. Multi-person, profile, heavy
      occlusion: the system flags these; do not force them.

## During the run

- [ ] Analyze first. Look at the whole picture (face and hands, neck, chest, hair), not just
      the eyes.
- [ ] Calibrate per photo. A small or low-resolution face never gets a raw paste; pigment is
      generative-led; mild unevenness is deterministic only; hair is generative only.
- [ ] Pasting on a large face: always color-match the donor to clean skin, never drag the
      donor's color.
- [ ] Masks are organic and wide-feathered. A straight mask edge is a rectangular tell.
- [ ] Re-apply the brow/eye/lip/lash protect AFTER feathering, in every layer.

## Before delivering

- [ ] Audit at nearest-neighbor native resolution. Interpolated zoom hides artifacts; it has
      fooled this project repeatedly. Never verify on a smooth-scaled preview.
- [ ] Every mapped region has a verdict. A region you cannot check is not clean.
- [ ] No box or seam at any mask boundary.
- [ ] No blur or plastic skin: region texture matches the local skin baseline.
- [ ] No stipple: no injected high-frequency noise.
- [ ] No color cast or rouge: region tone matches the clean-skin reference.
- [ ] No residual mark: re-scan the edited region for any pigment or dark spot left behind.
- [ ] Lashes and brows preserved: the feather did not bleed onto them.
- [ ] Identity passes (ArcFace, or the defined SSIM fallback). Not skipped.
- [ ] If no candidate is clean, refuse and report. Do not ship the least-bad.

## After delivering

- [ ] The JSON telemetry report is written next to the output (assessment, calibration and
      rationale per region, sample scores, verdicts, identity, delivered).
- [ ] Never commit Gary's real photos. `inputs/` is gitignored; delivered files live in
      Google Drive, not the repo.
- [ ] Never print or commit the Gemini key (`~/Desktop/gemini.txt`).
