#!/usr/bin/env python3
"""
Idempotent Managed Agents provisioner for the booked-revenue demo agent.

Requires:
  - Managed Agents enabled in the Aiven Console for the project
    (Agents -> Request access -> Enable agents)
  - Aiven auth token (AIVEN_AUTH_TOKEN or ~/.config/aiven/aiven-credentials.json)
  - PyYAML (pip install pyyaml)
  - AUTO_ONTOLOGY_MCP_PUBLIC_URL and AUTO_ONTOLOGY_MCP_TOKEN (AO API token Bearer)
  - Optional: DATAHUB_MCP_URL, DATAHUB_GMS_TOKEN in .env

Mint an AO token (frontend must be up):
  python3 scripts/mint_auto_ontology_api_token.py

Usage:
  python3 scripts/provision_managed_agent.py
  python3 scripts/provision_managed_agent.py --recipe demo/agents/booked-revenue.yaml
  python3 scripts/provision_managed_agent.py --project shutchinson-demo

Does not open chat sessions or send demo prompts (Console Chat is the live path).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECIPE = ROOT / "demo" / "agents" / "booked-revenue.yaml"
API_BASE = os.environ.get("AIVEN_API_URL", "https://api.aiven.io").rstrip("/")
CREDENTIALS_PATH = Path(
    os.environ.get(
        "AIVEN_CREDENTIALS_FILE",
        Path.home() / ".config" / "aiven" / "aiven-credentials.json",
    )
)


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


def require_yaml() -> Any:
    try:
        import yaml  # type: ignore
    except ImportError as exc:  # noqa: BLE001
        print(
            "PyYAML is required. Install with: pip install pyyaml\n"
            f"({exc})",
            file=sys.stderr,
        )
        raise SystemExit(2) from exc
    return yaml


def load_recipe(path: Path) -> dict[str, Any]:
    yaml = require_yaml()
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise SystemExit(f"Recipe must be a mapping: {path}")
    for key in ("name", "model", "system_instructions"):
        if not data.get(key):
            raise SystemExit(f"Recipe missing required key {key!r}: {path}")
    return data


def auth_token() -> str:
    tok = os.environ.get("AIVEN_AUTH_TOKEN", "").strip()
    if tok:
        return tok
    if CREDENTIALS_PATH.is_file():
        data = json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))
        tok = (data.get("auth_token") or data.get("access_token") or "").strip()
        if tok:
            return tok
    raise SystemExit(
        "No Aiven auth token. Set AIVEN_AUTH_TOKEN or log in with avn "
        f"(expected credentials at {CREDENTIALS_PATH})."
    )


class AivenClient:
    def __init__(self, token: str, organization_id: str, project: str) -> None:
        self.token = token
        self.organization_id = organization_id
        self.project = project

    def _url(self, suffix: str) -> str:
        return (
            f"{API_BASE}/v1/organization/{self.organization_id}"
            f"/project/{self.project}/managed-agents/{suffix.lstrip('/')}"
        )

    def request(
        self,
        method: str,
        suffix: str,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            self._url(suffix),
            data=data,
            method=method,
            headers={
                "Authorization": f"aivenv1 {self.token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"{method} {suffix} failed HTTP {e.code}: {err_body}"
            ) from e


def resolve_organization_id(token: str, project: str) -> str:
    req = urllib.request.Request(
        f"{API_BASE}/v1/project/{project}",
        headers={"Authorization": f"aivenv1 {token}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise SystemExit(
            f"Failed to resolve project {project!r}: HTTP {e.code} {e.read().decode()}"
        ) from e
    proj = payload.get("project") if isinstance(payload.get("project"), dict) else payload
    org = proj.get("organization_id") or payload.get("organization_id")
    if not org:
        raise SystemExit(f"No organization_id on project {project!r}: {payload!r}")
    return str(org)


def mcp_url_from_base(raw: str) -> str:
    url = raw.strip().rstrip("/")
    if not url:
        return ""
    if url.endswith("/mcp"):
        return url
    return f"{url}/mcp"


def environment_name(client: AivenClient) -> str:
    data = client.request("GET", "environment")
    envs = data.get("environments") or []
    if not envs:
        print(
            "Managed Agents is not enabled for this project (environments is empty).\n"
            "In the Aiven Console:\n"
            f"  1. Open project {client.project}\n"
            "  2. Agents -> Request access (if needed)\n"
            "  3. Enable agents\n"
            "Then re-run this script.\n"
            "Docs: https://aiven.io/docs/tools/agents#enable-managed-agents",
            file=sys.stderr,
        )
        raise SystemExit(1)
    if isinstance(envs[0], str):
        return envs[0]
    if isinstance(envs[0], dict):
        name = envs[0].get("name") or envs[0].get("id") or envs[0].get("environment")
        if name:
            return str(name)
    raise SystemExit(f"Unexpected environments payload: {data!r}")


def list_integrations(client: AivenClient, environment: str) -> list[dict[str, Any]]:
    data = client.request("GET", f"environment/{environment}/integration")
    items = data.get("integrations") or []
    return [i for i in items if isinstance(i, dict)]


def delete_integration(client: AivenClient, environment: str, name: str) -> None:
    client.request(
        "DELETE",
        f"environment/{environment}/integration/{name}",
    )
    print(f"  Deleted integration {name!r}")


def tool_ids_from_integrations(
    integrations: list[dict[str, Any]],
    names: set[str],
) -> list[str]:
    ids: list[str] = []
    for integ in integrations:
        iname = integ.get("integration_name") or integ.get("name") or ""
        if names and iname not in names:
            continue
        status = (integ.get("status") or "").lower()
        if status and status not in ("connected", "ok", "ready", "active"):
            detail = integ.get("status_detail") or status
            print(f"  WARNING: integration {iname!r} status={status}: {detail}", file=sys.stderr)
        for tool in integ.get("tools") or []:
            if isinstance(tool, dict) and tool.get("id"):
                ids.append(str(tool["id"]))
    return ids


def connect_integration(
    client: AivenClient,
    *,
    environment: str,
    name: str,
    catalog_type: str,
    custom_url: str,
    token: str,
    read_only: bool,
    replace: bool,
) -> list[str]:
    if not token or token == "unused":
        raise SystemExit(
            f"Refusing to connect {name!r} without a real token. "
            "Set the recipe token_env (AUTO_ONTOLOGY_MCP_TOKEN for Auto Ontology)."
        )

    existing = {
        (i.get("integration_name") or i.get("name"))
        for i in list_integrations(client, environment)
    }
    if name in existing and replace:
        try:
            delete_integration(client, environment, name)
        except RuntimeError as exc:
            print(f"  WARNING: could not delete {name!r} before recreate: {exc}", file=sys.stderr)

    body: dict[str, Any] = {
        "catalog_type": catalog_type,
        "name": name,
        "custom_url": custom_url,
        "read_only": read_only,
        "token": token,
    }
    try:
        data = client.request(
            "POST",
            f"environment/{environment}/integration",
            body,
        )
    except RuntimeError as exc:
        msg = str(exc)
        if "already" in msg.lower() or "409" in msg or "conflict" in msg.lower():
            if replace:
                raise
            print(f"  Integration {name!r} already present; reusing.")
            return tool_ids_from_integrations(
                list_integrations(client, environment), {name}
            )
        raise
    tools = data.get("tools") or []
    ids = [t["id"] for t in tools if isinstance(t, dict) and t.get("id")]
    status = data.get("status") or "ok"
    detail = data.get("status_detail")
    print(f"  Connected integration {name!r} status={status} tools={len(ids)}")
    if detail:
        print(f"    detail: {detail}")
    if not ids:
        ids = tool_ids_from_integrations(
            list_integrations(client, environment), {name}
        )
    return ids


def list_agents(client: AivenClient) -> list[dict[str, Any]]:
    try:
        data = client.request("GET", "agent")
    except RuntimeError as exc:
        if "404" in str(exc):
            return []
        raise
    agents = data.get("agents") or []
    return [a for a in agents if isinstance(a, dict)]


def upsert_agent(
    client: AivenClient,
    *,
    environment: str,
    name: str,
    model: str,
    system_instructions: str,
    tool_ids: list[str],
) -> dict[str, Any]:
    existing = next((a for a in list_agents(client) if a.get("name") == name), None)
    if existing and existing.get("id"):
        body: dict[str, Any] = {
            "environment": environment,
            "name": name,
            "model": model,
            "system_instructions": system_instructions,
        }
        if tool_ids:
            body["tool_ids"] = tool_ids
        data = client.request("PATCH", f"agent/{existing['id']}", body)
        print(f"  Updated agent {name!r} id={existing['id']}")
        return data or existing
    body = {
        "environment": environment,
        "name": name,
        "model": model,
        "system_instructions": system_instructions,
        "tool_ids": tool_ids,
    }
    data = client.request("POST", "agent", body)
    print(f"  Created agent {name!r} id={data.get('id')}")
    return data


def integration_specs(recipe: dict[str, Any]) -> list[dict[str, Any]]:
    raw = recipe.get("integrations") or {}
    out: list[dict[str, Any]] = []
    for key in ("auto_ontology", "datahub"):
        if key not in raw:
            continue
        spec = raw[key]
        if not isinstance(spec, dict):
            continue
        out.append({"key": key, **spec})
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Provision the booked-revenue Managed Agent for this demo."
    )
    parser.add_argument(
        "--recipe",
        type=Path,
        default=DEFAULT_RECIPE,
        help=f"Agent recipe YAML (default: {DEFAULT_RECIPE})",
    )
    parser.add_argument(
        "--project",
        default=os.environ.get("AIVEN_PROJECT", "shutchinson-demo"),
        help="Aiven project name",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=ROOT / ".env",
        help="Optional dotenv file to load when vars are unset",
    )
    args = parser.parse_args()

    load_dotenv(args.env_file)
    recipe = load_recipe(args.recipe)
    token = auth_token()
    project = args.project
    org = resolve_organization_id(token, project)
    client = AivenClient(token, org, project)

    print(f"Project={project} organization_id={org}", flush=True)
    environment = environment_name(client)
    print(f"Managed Agents environment={environment}", flush=True)

    tool_ids: list[str] = []
    missing_datahub = False

    for spec in integration_specs(recipe):
        url_env = spec.get("url_env") or ""
        raw_url = os.environ.get(url_env, "").strip() if url_env else ""
        name = str(spec.get("name") or spec["key"])
        catalog_type = str(spec.get("catalog_type") or "custom")
        read_only = bool(spec.get("read_only", True))
        token_env = spec.get("token_env") or ""
        integ_token = os.environ.get(token_env, "").strip() if token_env else ""

        replace = bool(spec.get("replace", spec["key"] == "auto_ontology"))

        if spec["key"] == "auto_ontology":
            custom_url = mcp_url_from_base(raw_url)
            if not custom_url:
                raise SystemExit(
                    f"{url_env} unset. Set AUTO_ONTOLOGY_MCP_PUBLIC_URL to the public MCP base."
                )
            if not integ_token:
                raise SystemExit(
                    f"{token_env or 'AUTO_ONTOLOGY_MCP_TOKEN'} unset.\n"
                    "Mint one with: python3 scripts/mint_auto_ontology_api_token.py\n"
                    "(requires Auto Ontology frontend up), then add AUTO_ONTOLOGY_MCP_TOKEN to .env."
                )
            tool_ids.extend(
                connect_integration(
                    client,
                    environment=environment,
                    name=name,
                    catalog_type=catalog_type,
                    custom_url=custom_url,
                    token=integ_token,
                    read_only=read_only,
                    replace=replace,
                )
            )
            continue

        if spec["key"] == "datahub":
            custom_url = raw_url.rstrip("/")
            if not custom_url:
                missing_datahub = True
                print(
                    f"  WARNING: {url_env} unset; Managed Agents needs an HTTP MCP URL "
                    "(Cursor still uses uvx + DATAHUB_GMS_*).\n"
                    "  Console fallback: Agents -> Integrations -> Add custom integration,\n"
                    f"  name={name!r}, point at your DataHub HTTP MCP, then attach tools to the agent.",
                    file=sys.stderr,
                )
                continue
            if not integ_token:
                raise SystemExit(
                    f"{token_env or 'DATAHUB_GMS_TOKEN'} unset for DataHub HTTP MCP."
                )
            tool_ids.extend(
                connect_integration(
                    client,
                    environment=environment,
                    name=name,
                    catalog_type=catalog_type,
                    custom_url=custom_url,
                    token=integ_token,
                    read_only=read_only,
                    replace=replace,
                )
            )

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_tools: list[str] = []
    for tid in tool_ids:
        if tid not in seen:
            seen.add(tid)
            unique_tools.append(tid)

    agent = upsert_agent(
        client,
        environment=environment,
        name=str(recipe["name"]),
        model=str(recipe["model"]),
        system_instructions=str(recipe["system_instructions"]).strip(),
        tool_ids=unique_tools,
    )

    # Refresh agent view for tools display
    refreshed = next(
        (a for a in list_agents(client) if a.get("name") == recipe["name"]),
        agent,
    )
    tools = refreshed.get("tools") or agent.get("tools") or []
    tool_names = [
        t.get("name") or t.get("id")
        for t in tools
        if isinstance(t, dict)
    ]

    print()
    print("Done.")
    print(f"  agent_id: {refreshed.get('id') or agent.get('id')}")
    print(f"  name:     {recipe['name']}")
    print(f"  model:    {recipe['model']}")
    print(f"  tools:    {tool_names or unique_tools or '(none returned; check Console Integrations)'}")
    if missing_datahub:
        print("  note:     Attach DataHub MCP in Console before Act 4 Path B.")
    print()
    print("Console Chat:")
    print(f"  https://console.aiven.io/account/{org}/project/{project}/agents")
    print(f"  -> open agent {recipe['name']!r} -> Chat")
    print()
    prompts = recipe.get("demo_prompts") or {}
    if prompts:
        print("Demo prompts (run in order):")
        for key in ("pii_fail", "uncertified_fail", "certified_success"):
            if key in prompts:
                text = " ".join(str(prompts[key]).split())
                print(f"  [{key}] {text}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
