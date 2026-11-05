# KubeCon Demo Video Implementation Plan

> **For agentic workers:** Implement task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Produce `demo/video/out/demo_teaser.mp4` from a storyboard via capture, edge-tts, and ffmpeg.

**Architecture:** YAML storyboard drives Playwright frames, TTS audio, and ffmpeg assemble. Fixture mode rebuilds offline.

**Tech Stack:** Python 3, Playwright, edge-tts, ffmpeg, PyYAML

## Tasks

- [x] Design spec
- [ ] storyboard.yaml + static HTML cards
- [ ] capture_shots.py
- [ ] synthesize_vo.py
- [ ] assemble_video.py
- [ ] build.sh + docs + gitignore
- [ ] Fixture-mode verify build
