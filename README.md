# Actor Headshot Retouch Skill

This is a Codex skill for actor, model, casting, agency, and commercial headshot retouching.

It is built for three workflows:

- **Light retouching:** for photos that are already strong and only need minor local polish.
- **Hybrid map:** the default path. Use image generation to create a retouch map/proof, then transfer accepted fixes back onto the original full-resolution structure.
- **Light regen:** for photos that need max-quality imagegen rescue work around tired eyes, under-eyes, discoloration, eye whites, neck, hands, or skin fatigue.

The skill starts with a readiness checklist before doing any edit. It is designed to preserve identity and avoid fake, AI-looking results.

By default, the skill assumes you want material, human-visible improvement. It rejects retouches that are technically changed but impossible to see.

## What To Install

Copy the entire folder named:

```text
actor-headshot-retouch
```

into your Codex skills folder.

Do not copy only `SKILL.md`. The whole folder matters because it includes the readiness checker and workflow guide.

## Mac / Linux Install

Copy and paste this into Terminal from the folder where you downloaded this repo:

```bash
mkdir -p ~/.codex/skills
cp -R actor-headshot-retouch ~/.codex/skills/
```

Then restart Codex or open a new Codex thread.

Use it by typing:

```text
Use $actor-headshot-retouch on this headshot.
```

## Windows Install

Copy and paste this into PowerShell from the folder where you downloaded this repo:

```powershell
New-Item -ItemType Directory -Force $env:USERPROFILE\.codex\skills
Copy-Item -Recurse actor-headshot-retouch $env:USERPROFILE\.codex\skills\
```

Then restart Codex or open a new Codex thread.

Use it by typing:

```text
Use $actor-headshot-retouch on this headshot.
```

## Optional Photo Tools

For local and hybrid-map retouching, install:

- Python 3.12
- ImageMagick
- libvips
- ExifTool

Then install the Python image packages:

```bash
python -m venv photo-retouch
python -m pip install --upgrade pip wheel setuptools
python -m pip install numpy pillow opencv-python scikit-image mediapipe rawpy pyvips
```

You do **not** need PyYAML to use this skill.

## What The Skill Checks

Before editing, the skill checks:

- Python imaging stack
- ImageMagick
- libvips
- ExifTool
- whether image generation is available for hybrid-map and light regen
- whether the source image can be read
- whether the output folder can be written

If something required is missing, the skill stops before editing.

## What Changed In v1.2.0

- Added `hybrid-map` as the explicit default workflow.
- Added readiness support for `--mode hybrid-map`.
- Made image generation a retouch-map/proof step before transferring accepted fixes back to the original full-resolution structure.
- Added clearer escalation rules for max-quality light regen when local or hybrid fixes cannot visibly solve hard eye, skin, thumb, or neck issues.
- Added specific guardrails against cheek bleaching, broad blur, face-shape drift, annotation marks, old reference artifacts, and invisible edits.

## What Changed In v1.1.0

- Added a minimum viable edit threshold so invisible retouches are rejected.
- Added before/after QA expectations for full frame and 100% crops.
- Added a lightweight retouch operation log inspired by non-destructive photo workflows.
- Strengthened local retouching rules around targeted masks/selections.
- Strengthened light regen rules so low-detail or AI-looking outputs are proof candidates, not automatic finals.

The skill borrows workflow ideas from tools like PhotoFlow, darktable, RawTherapee, and GEGL, but it does **not** require installing them.
