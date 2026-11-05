#!/usr/bin/env python3
"""
Mint an Auto Ontology API token for Managed Agents MCP auth.

Signs in with AUTO_ONTOLOGY_ADMIN_EMAIL / AUTO_ONTOLOGY_ADMIN_PASSWORD against
the frontend (AUTO_ONTOLOGY_UI_URL, APP_URL, or the ao-auto-ontology-frontend
public URL), then POSTs /api/api-tokens.

Prints the plaintext token once. Add it to .env as AUTO_ONTOLOGY_MCP_TOKEN.

Usage:
  python3 scripts/mint_auto_ontology_api_token.py
  python3 scripts/mint_auto_ontology_api_token.py --name managed-agents-demo
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = val


def frontend_url(project: str) -> str:
    for key in ("AUTO_ONTOLOGY_UI_URL", "APP_URL"):
        val = os.environ.get(key, "").strip().rstrip("/")
        if val:
            return val
    # Resolve Runtime public URL from Aiven.
    try:
        raw = subprocess.check_output(
            [
                "avn",
                "service",
                "get",
                "ao-auto-ontology-frontend",
                "--project",
                project,
                "--json",
            ],
            text=True,
        )
        data = json.loads(raw)
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as exc:
        raise SystemExit(
            "Set AUTO_ONTOLOGY_UI_URL (or APP_URL) to the public frontend, "
            f"or ensure avn can read ao-auto-ontology-frontend ({exc})."
        ) from exc
    for comp in data.get("components") or []:
        if comp.get("component") == "http":
            path = comp.get("path")
            if path:
                return str(path).rstrip("/")
            host = comp.get("host")
            if host:
                return f"https://{host}"
    raise SystemExit("No http component on ao-auto-ontology-frontend")


def main() -> int:
    parser = argparse.ArgumentParser(description="Mint Auto Ontology API token for MCP.")
    parser.add_argument("--name", default="managed-agents-demo", help="Token label")
    parser.add_argument(
        "--project",
        default=os.environ.get("AIVEN_PROJECT", "shutchinson-demo"),
    )
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument(
        "--expires-in-days",
        type=int,
        default=90,
        help="Token lifetime in days (default 90)",
    )
    args = parser.parse_args()
    load_dotenv(args.env_file)

    email = os.environ.get("AUTO_ONTOLOGY_ADMIN_EMAIL", "").strip()
    password = os.environ.get("AUTO_ONTOLOGY_ADMIN_PASSWORD", "").strip()
    if not email or not password:
        raise SystemExit("Set AUTO_ONTOLOGY_ADMIN_EMAIL and AUTO_ONTOLOGY_ADMIN_PASSWORD")

    base = frontend_url(args.project)
    print(f"Frontend: {base}", flush=True)

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    sign_in_body = json.dumps({"email": email, "password": password}).encode("utf-8")
    sign_req = urllib.request.Request(
        f"{base}/api/auth/sign-in/email",
        data=sign_in_body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": base,
        },
    )
    try:
        with opener.open(sign_req, timeout=60) as resp:
            _ = resp.read()
            print(f"Signed in as {email} (HTTP {resp.status})", flush=True)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Sign-in failed HTTP {e.code}: {body}") from e

    mint_body = json.dumps(
        {"name": args.name, "expires_in_days": args.expires_in_days}
    ).encode("utf-8")
    mint_req = urllib.request.Request(
        f"{base}/api/api-tokens",
        data=mint_body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": base,
        },
    )
    try:
        with opener.open(mint_req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Mint token failed HTTP {e.code}: {body}") from e

    token = payload.get("token") or payload.get("key") or payload.get("value")
    if not token:
        raise SystemExit(f"No plaintext token in response: {payload!r}")

    print()
    print("Add to .env (shown once):")
    print(f"AUTO_ONTOLOGY_MCP_TOKEN={token}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
