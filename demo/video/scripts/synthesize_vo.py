#!/usr/bin/env python3
"""Synthesize per-beat voiceover with edge-tts (default) or OpenAI TTS."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_storyboard(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def audio_duration_s(path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    out = subprocess.check_output(cmd, text=True).strip()
    return float(out)


async def edge_tts_save(text: str, voice: str, dest: Path) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(dest))


def openai_tts_save(text: str, dest: Path) -> None:
    import urllib.request

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY required for openai TTS")
    model = os.environ.get("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
    voice = os.environ.get("OPENAI_TTS_VOICE", "alloy")
    body = json.dumps({"model": model, "voice": voice, "input": text, "format": "mp3"}).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/audio/speech",
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        dest.write_bytes(resp.read())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storyboard", type=Path, default=ROOT / "storyboard.yaml")
    parser.add_argument("--out", type=Path, default=ROOT / "out" / "audio")
    parser.add_argument("--engine", choices=("edge", "openai"), default=os.environ.get("DEMO_VIDEO_TTS", "edge"))
    args = parser.parse_args()

    if shutil_which("ffprobe") is None:
        print("ERROR: ffprobe (ffmpeg) is required", file=sys.stderr)
        return 1

    sb = load_storyboard(args.storyboard)
    voice = sb.get("voice", "en-US-GuyNeural")
    args.out.mkdir(parents=True, exist_ok=True)
    meta: list[dict] = []

    for idx, beat in enumerate(sb["beats"], start=1):
        beat_id = beat["id"]
        text = " ".join(str(beat.get("vo", "")).split())
        dest = args.out / f"{idx:02d}-{beat_id}.mp3"
        print(f"[{idx:02d}] TTS {beat_id} ({args.engine})")
        if args.engine == "openai":
            openai_tts_save(text, dest)
        else:
            asyncio.run(edge_tts_save(text, voice, dest))
        dur = audio_duration_s(dest)
        hold = float(beat.get("hold_ms", 0)) / 1000.0
        # hold_ms is pause AFTER narration (extends the still while audio has ended)
        total = dur + hold
        meta.append(
            {
                "id": beat_id,
                "index": idx,
                "audio": dest.name,
                "audio_s": dur,
                "hold_s": hold,
                "duration_s": total,
            }
        )
        print(f"  {dur:.2f}s audio + {hold:.2f}s hold -> {total:.2f}s")

    meta_path = args.out / "manifest.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Wrote {meta_path}")
    return 0


def shutil_which(cmd: str) -> str | None:
    from shutil import which

    return which(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
