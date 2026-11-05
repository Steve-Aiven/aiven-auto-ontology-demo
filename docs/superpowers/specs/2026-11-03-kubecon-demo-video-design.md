# Design: KubeCon demo video (DataHub + Auto Ontology)

Date: 2026-11-03

## Goal

Ship a reproducible ~2.5 to 3 minute open-source teaser video for KubeCon: headless screenshots, TTS narration, ffmpeg assembly. Story matches the live walkthrough: conflicting revenue, DataHub as map/rulebook, Auto Ontology as certified calculator, punchline **717000**.

## Decisions

- Approach: manifest-driven Ken Burns slideshow (`storyboard.yaml`).
- Capture: Playwright Chromium (live URLs) with `DEMO_VIDEO_FIXTURE=1` offline rebuild from committed fixtures.
- TTS: `edge-tts` default (no API key). Optional OpenAI TTS via env only.
- Output: `demo/video/out/demo_teaser.mp4` at 1920x1080.
- No music bed, no burned-in captions, no Cursor UI automation in v1.

## Beats

1. Cold open (three revenue trap)
2. Estate overview
3. DataHub map / Finance ownership
4. Lineage Kafka to ClickHouse to landing to invoices
5. PII gate on `billing_email`
6. Auto Ontology certified `booked_revenue`
7. Punchline 717000 USD
8. Close / open-source CTA

## Non-goals

- Full live walkthrough length (~20 min)
- CI against live Aiven
- Multi-language VO
