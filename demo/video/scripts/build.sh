#!/usr/bin/env bash
# Build the KubeCon teaser: capture -> TTS -> assemble
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$ROOT/../.." && pwd)"
cd "$REPO"

# Load KEY=VALUE from .env without evaluating shell syntax in values.
if [[ -f .env ]]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" || "$line" == \#* ]] && continue
    [[ "$line" != *=* ]] && continue
    key="${line%%=*}"
    val="${line#*=}"
    key="${key%"${key##*[![:space:]]}"}"
    key="${key#"${key%%[![:space:]]*}"}"
    val="${val%$'\r'}"
    if [[ "$val" == \"*\" && "$val" == *\" ]]; then
      val="${val:1:${#val}-2}"
    elif [[ "$val" == \'*\' && "$val" == *\' ]]; then
      val="${val:1:${#val}-2}"
    fi
    export "$key=$val"
  done < .env
fi

FIXTURE="${DEMO_VIDEO_FIXTURE:-1}"
if [[ -n "${DEMO_VIDEO_PYTHON:-}" ]]; then
  PY="$DEMO_VIDEO_PYTHON"
elif [[ -x "$REPO/.venv/bin/python" ]]; then
  PY="$REPO/.venv/bin/python"
elif [[ -x "$ROOT/.venv/bin/python" ]]; then
  PY="$ROOT/.venv/bin/python"
else
  python3 -m venv "$ROOT/.venv"
  PY="$ROOT/.venv/bin/python"
fi

if ! command -v ffmpeg >/dev/null; then
  echo "ffmpeg is required (brew install ffmpeg)" >&2
  exit 1
fi

"$PY" -c "import playwright, edge_tts, yaml" 2>/dev/null || {
  echo "Installing demo/video Python deps into $PY ..."
  "$PY" -m pip install -q -r "$ROOT/requirements.txt"
  "$PY" -m playwright install chromium
}

export DEMO_VIDEO_FIXTURE="$FIXTURE"
echo "== capture (DEMO_VIDEO_FIXTURE=$FIXTURE) =="
"$PY" "$ROOT/scripts/capture_shots.py" --write-fixtures

echo "== TTS =="
"$PY" "$ROOT/scripts/synthesize_vo.py"

echo "== assemble =="
"$PY" "$ROOT/scripts/assemble_video.py"

echo "Done: $ROOT/out/demo_teaser.mp4"
ls -lh "$ROOT/out/demo_teaser.mp4"
