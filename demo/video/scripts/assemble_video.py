#!/usr/bin/env python3
"""Assemble Ken Burns stills + per-beat audio into demo_teaser.mp4."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.check_call(cmd)


def load_storyboard(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storyboard", type=Path, default=ROOT / "storyboard.yaml")
    parser.add_argument("--frames", type=Path, default=ROOT / "out" / "frames")
    parser.add_argument("--audio", type=Path, default=ROOT / "out" / "audio")
    parser.add_argument("--out", type=Path, default=ROOT / "out" / "demo_teaser.mp4")
    args = parser.parse_args()

    sb = load_storyboard(args.storyboard)
    width = int(sb.get("width", 1920))
    height = int(sb.get("height", 1080))
    crossfade = float(sb.get("crossfade_s", 0.3))
    ken = bool(sb.get("ken_burns", True))
    meta = json.loads((args.audio / "manifest.json").read_text(encoding="utf-8"))

    args.out.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="demo-video-") as tmp:
        tmp_path = Path(tmp)
        clip_paths: list[Path] = []
        for item in meta:
            idx = int(item["index"])
            beat_id = item["id"]
            frame = args.frames / f"{idx:02d}-{beat_id}.png"
            audio = args.audio / item["audio"]
            if not frame.exists():
                print(f"ERROR: missing frame {frame}", file=sys.stderr)
                return 1
            if not audio.exists():
                print(f"ERROR: missing audio {audio}", file=sys.stderr)
                return 1
            dur = float(item["duration_s"])
            clip = tmp_path / f"clip-{idx:02d}.mp4"
            # Mild Ken Burns: slow zoom 1.0 -> 1.06 over the clip.
            if ken:
                vf = (
                    f"scale={width*2}:{height*2},"
                    f"zoompan=z='min(1.06,1+0.06*on/{max(dur*30,1)})':"
                    f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                    f"d={max(int(dur * 30), 1)}:s={width}x{height}:fps=30,"
                    f"format=yuv420p"
                )
            else:
                vf = f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                vf += f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,format=yuv420p"

            # Pad audio with silence for post-VO hold so video and audio share duration_s.
            hold_s = float(item.get("hold_s", 0))
            audio_input = str(audio)
            if hold_s > 0.05:
                padded = tmp_path / f"audio-pad-{idx:02d}.m4a"
                run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        str(audio),
                        "-af",
                        f"apad=pad_dur={hold_s:.3f}",
                        "-c:a",
                        "aac",
                        "-b:a",
                        "192k",
                        str(padded),
                    ]
                )
                audio_input = str(padded)
            run(
                [
                    "ffmpeg",
                    "-y",
                    "-loop",
                    "1",
                    "-i",
                    str(frame),
                    "-i",
                    audio_input,
                    "-vf",
                    vf,
                    "-c:v",
                    "libx264",
                    "-tune",
                    "stillimage",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-t",
                    f"{dur:.3f}",
                    "-pix_fmt",
                    "yuv420p",
                    str(clip),
                ]
            )
            clip_paths.append(clip)

        # Concat with optional xfade is complex with audio; use simple concat demuxer.
        # Crossfade skipped when clips are short; keep cut edits for reliability.
        list_file = tmp_path / "concat.txt"
        list_file.write_text(
            "".join(f"file '{p}'\n" for p in clip_paths),
            encoding="utf-8",
        )
        # Note: crossfade retained in storyboard for future; v1 uses hard cuts for A/V sync.
        _ = crossfade
        run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-c",
                "copy",
                str(args.out),
            ]
        )

    # Probe final duration
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(args.out),
        ],
        text=True,
    ).strip()
    print(f"Wrote {args.out} ({float(out):.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
