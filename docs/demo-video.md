# KubeCon demo video

Build a ~2.5 to 3 minute TTS-narrated teaser from screenshots.

## Prereqs

- `ffmpeg` / `ffprobe` (`brew install ffmpeg`)
- Python 3 + `demo/video/requirements.txt` (Playwright, edge-tts, PyYAML)
- Chromium via `python3 -m playwright install chromium`

## Offline rebuild (show floor)

```bash
DEMO_VIDEO_FIXTURE=1 ./demo/video/scripts/build.sh
```

Uses static HTML cards (and any PNGs under `demo/video/fixtures/`). Output: `demo/video/out/demo_teaser.mp4`.

## Live capture (real product screenshots)

Beats 02–07 prefer live UI (DataHub search / lineage / PII / glossary or Auto Ontology, plus the agent harness for the punchline). Beats 01 and 08 stay as title cards.

1. Power on Aiven services in `shutchinson-demo` (especially `ao-datahub` and companions; `ao-auto-ontology-frontend` for AO UI shots).
2. Put UI credentials in `.env` or `demo/video/out/capture.env` (gitignored via `out/`):
   - `DATAHUB_UI_URL`, `DATAHUB_UI_USER`, `DATAHUB_UI_PASSWORD`
   - `AUTO_ONTOLOGY_UI_URL` or `APP_URL`, plus admin email/password
3. Rebuild with live capture (and refresh fixtures):

```bash
# Helper: refresh capture.env from Aiven DataHub connection info
avn service get ao-datahub --project shutchinson-demo --json | python3 -c '
import json,sys,os
ci=json.load(sys.stdin).get("connection_info") or {}
os.makedirs("demo/video/out", exist_ok=True)
open("demo/video/out/capture.env","w").write(
  f"DATAHUB_UI_URL={ci.get(\"frontend_url\",\"\")}\n"
  f"DATAHUB_UI_USER={ci.get(\"user\",\"datahub\")}\n"
  f"DATAHUB_UI_PASSWORD={ci.get(\"password\",\"\")}\n"
)
'
DEMO_VIDEO_FIXTURE=0 ./demo/video/scripts/build.sh
```

If a live step fails (AO frontend powered off, selector miss), that beat falls back to its static card or DataHub glossary, then continues.

## Edit the talk track

Edit VO and shot metadata in [`demo/video/storyboard.yaml`](../demo/video/storyboard.yaml), then rebuild.

## Design

See [`docs/superpowers/specs/2026-11-03-kubecon-demo-video-design.md`](superpowers/specs/2026-11-03-kubecon-demo-video-design.md).
