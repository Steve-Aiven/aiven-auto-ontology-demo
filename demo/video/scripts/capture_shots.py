#!/usr/bin/env python3
"""Capture storyboard frames via Playwright (live app UI preferred, static fallback)."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]


def load_dotenv_files() -> None:
    for env_path in (REPO / ".env", ROOT / "out" / "capture.env"):
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip("'").strip('"')
            # capture.env overrides .env for UI secrets used only for screenshots
            if env_path.name == "capture.env":
                os.environ[key] = val
            else:
                os.environ.setdefault(key, val)
    # Common aliases
    if not os.environ.get("AUTO_ONTOLOGY_UI_URL") and os.environ.get("APP_URL"):
        os.environ["AUTO_ONTOLOGY_UI_URL"] = os.environ["APP_URL"]


def load_storyboard(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_dirs(*paths: Path) -> None:
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)


def capture_static(page, html_path: Path, dest: Path, width: int, height: int) -> None:
    page.set_viewport_size({"width": width, "height": height})
    page.goto(html_path.resolve().as_uri(), wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(800)
    page.screenshot(path=str(dest), full_page=False)
    print(f"  static {html_path.name} -> {dest.name}")


def dismiss_modals(page) -> None:
    for sel in (
        '[aria-label="Close"]',
        "button.ant-modal-close",
        'button:has-text("Skip")',
        'button:has-text("Got it")',
    ):
        try:
            loc = page.locator(sel)
            if loc.count():
                loc.first.click(timeout=1500)
                page.wait_for_timeout(600)
        except Exception:
            pass


def datahub_login(page, base: str) -> None:
    user = os.environ.get("DATAHUB_UI_USER", "datahub")
    password = os.environ.get("DATAHUB_UI_PASSWORD", "")
    if not password:
        raise RuntimeError("DATAHUB_UI_PASSWORD required for live DataHub capture")
    page.goto(base.rstrip("/") + "/login", wait_until="networkidle", timeout=90000)
    page.fill("#username", user)
    page.fill("#password", password)
    page.get_by_role("button", name="Login").click()
    page.wait_for_timeout(3500)
    dismiss_modals(page)
    if "/login" in page.url:
        raise RuntimeError(f"DataHub login failed; still at {page.url}")
    print(f"  logged into DataHub ({page.url})")


def ao_login(page, base: str) -> None:
    email = os.environ.get("AUTO_ONTOLOGY_ADMIN_EMAIL", "")
    password = os.environ.get("AUTO_ONTOLOGY_ADMIN_PASSWORD", "")
    if not email or not password:
        raise RuntimeError("AUTO_ONTOLOGY_ADMIN_EMAIL/PASSWORD required for live AO capture")
    page.goto(base.rstrip("/") + "/", wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(2000)
    # If redirected to login
    for sel in ('input[type="email"]', 'input[name="email"]', "#email"):
        if page.locator(sel).count():
            page.fill(sel, email)
            break
    for sel in ('input[type="password"]', 'input[name="password"]', "#password"):
        if page.locator(sel).count():
            page.fill(sel, password)
            break
    for sel in ('button[type="submit"]', 'button:has-text("Sign in")', 'button:has-text("Log in")'):
        if page.locator(sel).count():
            page.click(sel)
            page.wait_for_timeout(3000)
            break
    print(f"  AO page ready ({page.url})")


def run_actions(page, base: str, actions: list[dict], width: int, height: int) -> None:
    page.set_viewport_size({"width": width, "height": height})
    for step in actions:
        kind = step.get("action")
        if kind == "goto":
            path = step.get("path", "/")
            url = path if path.startswith("http") else base.rstrip("/") + path
            page.goto(url, wait_until=step.get("wait_until", "domcontentloaded"), timeout=90000)
            page.wait_for_timeout(int(step.get("wait_ms", 2500)))
            dismiss_modals(page)
        elif kind == "click":
            sel = step["selector"]
            page.locator(sel).first.click(timeout=15000)
            page.wait_for_timeout(int(step.get("wait_ms", 2500)))
        elif kind == "click_text":
            page.get_by_text(step["text"], exact=bool(step.get("exact", False))).first.click(timeout=15000)
            page.wait_for_timeout(int(step.get("wait_ms", 2500)))
        elif kind == "click_role":
            page.get_by_role(step.get("role", "button"), name=step["name"]).click(timeout=15000)
            page.wait_for_timeout(int(step.get("wait_ms", 2500)))
        elif kind == "fill":
            page.fill(step["selector"], step["value"])
            page.wait_for_timeout(int(step.get("wait_ms", 500)))
        elif kind == "press":
            page.keyboard.press(step.get("key", "Enter"))
            page.wait_for_timeout(int(step.get("wait_ms", 1500)))
        elif kind == "wait":
            page.wait_for_timeout(int(step.get("wait_ms", 1000)))
        elif kind == "dismiss":
            dismiss_modals(page)
        else:
            raise RuntimeError(f"Unknown action {kind}")


def capture_harness(page, dest: Path, width: int, height: int) -> None:
    """Run agent harness and screenshot its terminal-style output as HTML."""
    harness = REPO / "scripts" / "agent_demo_harness.py"
    proc = subprocess.run(
        [sys.executable, str(harness)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    text = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"/>
<style>
body{{margin:0;background:#0b1220;color:#d7e2f5;font:18px/1.45 ui-monospace,Menlo,monospace}}
pre{{padding:48px 64px;white-space:pre-wrap}}
.ok{{color:#3ecf8e}}
h1{{font:600 28px/1.2 ui-sans-serif,system-ui;color:#3ecf8e;padding:48px 64px 0}}
</style></head><body>
<h1>Agent path · DataHub gates + certified answer</h1>
<pre>{_escape(text)}</pre></body></html>"""
    tmp = ROOT / "out" / "_harness.html"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(html, encoding="utf-8")
    page.set_viewport_size({"width": width, "height": height})
    page.goto(tmp.resolve().as_uri(), wait_until="networkidle")
    page.screenshot(path=str(dest), full_page=False)
    print(f"  harness -> {dest.name}")


def _escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storyboard", type=Path, default=ROOT / "storyboard.yaml")
    parser.add_argument("--out", type=Path, default=ROOT / "out" / "frames")
    parser.add_argument("--fixtures", type=Path, default=ROOT / "fixtures")
    parser.add_argument(
        "--fixture-mode",
        action="store_true",
        default=os.environ.get("DEMO_VIDEO_FIXTURE", "").lower() in ("1", "true", "yes"),
    )
    parser.add_argument("--prefer-live", action="store_true", default=False)
    parser.add_argument("--write-fixtures", action="store_true")
    args = parser.parse_args()
    load_dotenv_files()

    # Live unless fixture mode forced
    prefer_live = args.prefer_live or (
        not args.fixture_mode and bool(os.environ.get("DATAHUB_UI_URL"))
    )
    if os.environ.get("DEMO_VIDEO_FIXTURE", "").lower() in ("1", "true", "yes"):
        prefer_live = False
        args.fixture_mode = True

    sb = load_storyboard(args.storyboard)
    width = int(sb.get("width", 1920))
    height = int(sb.get("height", 1080))
    ensure_dirs(args.out, args.fixtures)

    from playwright.sync_api import sync_playwright

    datahub_base = os.environ.get("DATAHUB_UI_URL", "").rstrip("/")
    ao_base = os.environ.get("AUTO_ONTOLOGY_UI_URL", os.environ.get("APP_URL", "")).rstrip("/")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=1)
        page = context.new_page()
        logged_dh = False
        logged_ao = False

        for idx, beat in enumerate(sb["beats"], start=1):
            beat_id = beat["id"]
            dest = args.out / f"{idx:02d}-{beat_id}.png"
            print(f"[{idx:02d}] {beat_id}")
            cap = beat.get("capture") or {}

            if args.fixture_mode and not prefer_live:
                src = args.fixtures / f"{beat_id}.png"
                if src.exists():
                    shutil.copy2(src, dest)
                    print(f"  fixture {src.name}")
                    continue

            used_live = False
            live_specs = []
            if cap.get("live"):
                live_specs.append(cap["live"])
            if cap.get("live_fallback"):
                live_specs.append(cap["live_fallback"])

            if prefer_live and live_specs:
                for live in live_specs:
                    try:
                        kind = live.get("kind", "url")
                        if kind == "harness":
                            capture_harness(page, dest, width, height)
                            used_live = True
                        elif kind == "datahub":
                            if not datahub_base:
                                raise RuntimeError("DATAHUB_UI_URL unset")
                            if not logged_dh:
                                datahub_login(page, datahub_base)
                                logged_dh = True
                            run_actions(page, datahub_base, live.get("actions") or [], width, height)
                            page.screenshot(path=str(dest), full_page=False)
                            print(f"  datahub -> {dest.name} ({page.url})")
                            used_live = True
                        elif kind == "auto_ontology":
                            if not ao_base:
                                raise RuntimeError("AUTO_ONTOLOGY_UI_URL/APP_URL unset")
                            probe = context.new_page()
                            try:
                                resp = probe.goto(ao_base + "/", wait_until="domcontentloaded", timeout=20000)
                                status = resp.status if resp else 0
                                final = probe.url
                            finally:
                                probe.close()
                            if status >= 400 or "status?" in final or "aivencloud.net/services/status" in final:
                                raise RuntimeError(f"AO UI unavailable (HTTP {status})")
                            if not logged_ao:
                                ao_login(page, ao_base)
                                logged_ao = True
                            run_actions(page, ao_base, live.get("actions") or [], width, height)
                            page.screenshot(path=str(dest), full_page=False)
                            print(f"  auto_ontology -> {dest.name} ({page.url})")
                            used_live = True
                        elif kind == "url":
                            env_key = live.get("env_url", "DATAHUB_UI_URL")
                            base = os.environ.get(env_key, "").rstrip("/")
                            if not base:
                                raise RuntimeError(f"{env_key} unset")
                            if env_key.startswith("DATAHUB") and not logged_dh:
                                datahub_login(page, base)
                                logged_dh = True
                            path = live.get("path", "/")
                            page.goto(base + path, wait_until="domcontentloaded", timeout=90000)
                            page.wait_for_timeout(int(live.get("wait_ms", 3000)))
                            dismiss_modals(page)
                            page.screenshot(path=str(dest), full_page=False)
                            print(f"  url -> {dest.name}")
                            used_live = True
                        if used_live:
                            break
                    except Exception as e:  # noqa: BLE001
                        print(f"  live capture failed ({e}); trying next fallback")

            if not used_live:
                if cap.get("kind") == "static":
                    html_path = ROOT / cap["path"]
                    if not html_path.exists():
                        print(f"ERROR: missing {html_path}", file=sys.stderr)
                        return 1
                    capture_static(page, html_path, dest, width, height)
                elif (args.fixtures / f"{beat_id}.png").exists():
                    shutil.copy2(args.fixtures / f"{beat_id}.png", dest)
                    print(f"  fixture fallback {beat_id}.png")
                else:
                    print(f"ERROR: no capture for {beat_id}", file=sys.stderr)
                    return 1

            if args.write_fixtures or used_live:
                shutil.copy2(dest, args.fixtures / f"{beat_id}.png")
                print(f"  wrote fixture {beat_id}.png")

        browser.close()

    print(f"Frames ready under {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
