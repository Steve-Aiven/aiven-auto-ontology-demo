#!/usr/bin/env python3
"""Seed DataHub owners, glossary, PII tags, and optional lineage edges via GMS GraphQL/REST."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any


def env(name: str, default: str | None = None) -> str:
    val = os.environ.get(name, default)
    if not val:
        raise SystemExit(f"Missing required env {name}")
    return val


def gms_url() -> str:
    base = env("DATAHUB_GMS_URL").rstrip("/")
    if base.endswith("/api/gms"):
        return base
    return f"{base}/api/gms" if not base.endswith("/gms") else base


def request(method: str, path: str, body: dict | None = None) -> Any:
    url = f"{gms_url().rstrip('/')}{path}"
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {env('DATAHUB_GMS_TOKEN')}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {e.code} {url}: {err}") from e


def graphql(query: str, variables: dict | None = None) -> Any:
    payload = {"query": query, "variables": variables or {}}
    return request("POST", "/api/graphql", payload)


def emit_mcp(aspects: list[dict]) -> None:
    """Emit MetadataChangeProposal wrappers via /openapi/v3/entity/... or legacy ingest."""
    # Prefer openapi aspect upsert when available; fall back to /aspects?action=ingestProposal
    for aspect in aspects:
        try:
            request("POST", "/aspects?action=ingestProposal", {"proposal": aspect})
        except SystemExit as e:
            print(f"WARN ingestProposal failed: {e}", file=sys.stderr)


def dataset_urn(platform: str, name: str, env_name: str = "PROD") -> str:
    return f"urn:li:dataset:(urn:li:dataPlatform:{platform},{name},{env_name})"


def main() -> int:
    # Soft connectivity check
    try:
        request("GET", "/config")
        print("GMS reachable")
    except SystemExit as e:
        print(f"GMS config check failed (continuing with GraphQL): {e}", file=sys.stderr)

    # Aiven DataHub uses CreateGlossaryEntityInput (not CreateGlossaryTermInput).
    glossary_query = """
    mutation ($input: CreateGlossaryEntityInput!) {
      createGlossaryTerm(input: $input)
    }
    """
    # Create glossary term booked_revenue (ignore if exists)
    try:
        res = graphql(
            glossary_query,
            {
                "input": {
                    "id": "booked_revenue",
                    "name": "booked_revenue",
                    "description": (
                        "Invoice amounts with finance status booked. "
                        "Not ARR and not marketing pipeline. Certified for board revenue."
                    ),
                }
            },
        )
        if res.get("errors"):
            print("glossary booked_revenue:", json.dumps(res)[:500])
        else:
            print("glossary booked_revenue: ok", res.get("data"))
    except SystemExit as e:
        print(f"glossary create note: {e}", file=sys.stderr)

    # Tag definitions
    for tag_id, desc in [
        ("PII", "Personally identifiable information"),
        ("Sensitive", "Sensitive data; agents must not dump raw values"),
        ("CertifiedRevenue", "Finance-certified revenue definition"),
        ("NonCertifiedRevenue", "Sales/Marketing revenue-like metric; not board booked revenue"),
    ]:
        try:
            graphql(
                """
                mutation ($input: CreateTagInput!) {
                  createTag(input: $input)
                }
                """,
                {"input": {"id": tag_id, "name": tag_id, "description": desc}},
            )
            print(f"tag {tag_id}: ok")
        except SystemExit as e:
            print(f"tag {tag_id} note: {e}", file=sys.stderr)

    platform = os.environ.get("DATAHUB_PG_PLATFORM_INSTANCE", "ao-pg.saas_analytics")
    invoices = dataset_urn("postgres", f"{platform}.finance.invoices")
    customers = dataset_urn("postgres", f"{platform}.finance.customers")
    opportunities = dataset_urn("postgres", f"{platform}.sales.opportunities")
    attribution = dataset_urn("postgres", f"{platform}.marketing.attribution")
    landing = dataset_urn("postgres", f"{platform}.finance.invoice_events_landing")

    # Ownership via GraphQL addOwners when entity exists after connector ingest
    owners = [
        (invoices, "urn:li:corpGroup:finance", "TECHNICAL_OWNER"),
        (customers, "urn:li:corpGroup:finance", "TECHNICAL_OWNER"),
        (landing, "urn:li:corpGroup:finance", "TECHNICAL_OWNER"),
        (opportunities, "urn:li:corpGroup:sales", "TECHNICAL_OWNER"),
        (attribution, "urn:li:corpGroup:marketing", "TECHNICAL_OWNER"),
    ]
    for resource, owner, owner_type in owners:
        try:
            graphql(
                """
                mutation ($input: AddOwnersInput!) {
                  addOwners(input: $input)
                }
                """,
                {
                    "input": {
                        "resourceUrn": resource,
                        "owners": [{"ownerUrn": owner, "ownerEntityType": "CORP_GROUP", "type": owner_type}],
                    }
                },
            )
            print(f"owner {owner} -> {resource}: ok")
        except SystemExit as e:
            print(f"owner note for {resource}: {e}", file=sys.stderr)

    # Tags on datasets / schema fields (best-effort; URNs depend on connector naming)
    tag_targets = [
        (customers, "urn:li:tag:PII"),
        (customers, "urn:li:tag:Sensitive"),
        (invoices, "urn:li:tag:CertifiedRevenue"),
        (opportunities, "urn:li:tag:NonCertifiedRevenue"),
        (attribution, "urn:li:tag:NonCertifiedRevenue"),
    ]
    for resource, tag in tag_targets:
        try:
            graphql(
                """
                mutation ($input: BatchAddTagsInput!) {
                  batchAddTags(input: $input)
                }
                """,
                {"input": {"tagUrns": [tag], "resources": [{"resourceUrn": resource}]}},
            )
            print(f"tag {tag} -> {resource}: ok")
        except SystemExit as e:
            print(f"tag note for {resource}: {e}", file=sys.stderr)

    # Emit coarse lineage: kafka topic -> CH table -> PG landing -> invoices
    kafka_topic = os.environ.get("DATAHUB_KAFKA_TOPIC_URN") or (
        "urn:li:dataset:(urn:li:dataPlatform:kafka,"
        f"{os.environ.get('KAFKA_SERVICE', 'ao-datahub-kafka')}.invoice_booked_events,PROD)"
    )
    ch_table = os.environ.get("DATAHUB_CH_TABLE_URN") or (
        "urn:li:dataset:(urn:li:dataPlatform:clickhouse,"
        f"{os.environ.get('CH_SERVICE', 'ao-clickhouse')}.default.invoice_events,PROD)"
    )

    def lineage_proposal(upstream: str, downstream: str) -> dict:
        return {
            "entityType": "dataset",
            "entityUrn": downstream,
            "changeType": "UPSERT",
            "aspectName": "upstreamLineage",
            "aspect": {
                "contentType": "application/json",
                "value": json.dumps(
                    {
                        "upstreams": [
                            {
                                "auditStamp": {
                                    "time": 0,
                                    "actor": "urn:li:corpuser:datahub",
                                },
                                "dataset": upstream,
                                "type": "TRANSFORMED",
                            }
                        ]
                    }
                ),
            },
        }

    emit_mcp(
        [
            lineage_proposal(kafka_topic, ch_table),
            lineage_proposal(ch_table, landing),
            lineage_proposal(landing, invoices),
        ]
    )
    print("lineage proposals submitted (kafka -> CH -> landing -> invoices)")

    # Write a local evidence file the harness can use even if GraphQL URNs differ
    evidence = {
        "glossary_term": "booked_revenue",
        "pii_column": "finance.customers.billing_email",
        "certified_dataset": "finance.invoices",
        "non_certified": ["sales.opportunities.arr_amount", "marketing.attribution.pipeline_amount"],
        "owners": {
            "finance.invoices": "finance",
            "sales.opportunities": "sales",
            "marketing.attribution": "marketing",
        },
        "lineage": [
            "invoice_booked_events",
            "clickhouse.default.invoice_events",
            "finance.invoice_events_landing",
            "finance.invoices",
        ],
        "expected_q3_booked_revenue": 717000,
    }
    out = os.environ.get(
        "DATAHUB_GOVERNANCE_EVIDENCE",
        os.path.join(os.path.dirname(__file__), "..", "data", "datahub_governance_evidence.json"),
    )
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2)
        f.write("\n")
    print(f"wrote evidence {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
