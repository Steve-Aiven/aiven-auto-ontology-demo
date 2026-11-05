#!/usr/bin/env python3
"""Produce a handful of invoice booked events to Kafka for the demo lineage path."""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone

from confluent_kafka import Producer


EVENTS = [
    {"invoice_id": 1, "customer_id": 1, "booked_amount": 120000.0},
    {"invoice_id": 2, "customer_id": 1, "booked_amount": 120000.0},
    {"invoice_id": 3, "customer_id": 2, "booked_amount": 45000.0},
    {"invoice_id": 4, "customer_id": 2, "booked_amount": 45000.0},
    {"invoice_id": 5, "customer_id": 3, "booked_amount": 12000.0},
    {"invoice_id": 6, "customer_id": 4, "booked_amount": 200000.0},
    {"invoice_id": 8, "customer_id": 5, "booked_amount": 175000.0},
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", default=os.environ.get("KAFKA_BOOTSTRAP_SERVERS", ""))
    parser.add_argument("--topic", default=os.environ.get("KAFKA_TOPIC", "invoice_booked_events"))
    parser.add_argument(
        "--security-protocol",
        default=os.environ.get("KAFKA_SECURITY_PROTOCOL", "SSL"),
    )
    parser.add_argument("--username", default=os.environ.get("KAFKA_USERNAME", ""))
    parser.add_argument("--password", default=os.environ.get("KAFKA_PASSWORD", ""))
    args = parser.parse_args()

    if not args.bootstrap:
        print("KAFKA_BOOTSTRAP_SERVERS / --bootstrap is required", file=sys.stderr)
        return 1

    conf: dict = {
        "bootstrap.servers": args.bootstrap,
        "client.id": "ao-invoice-events-producer",
        "acks": "all",
        "security.protocol": args.security_protocol,
    }
    ca = os.environ.get("KAFKA_SSL_CAFILE") or os.environ.get("KAFKA_CA_PATH")
    cert = os.environ.get("KAFKA_SSL_CERTFILE")
    key = os.environ.get("KAFKA_SSL_KEYFILE")
    if ca:
        conf["ssl.ca.location"] = ca
    if cert:
        conf["ssl.certificate.location"] = cert
    if key:
        conf["ssl.key.location"] = key
    if args.username:
        conf["security.protocol"] = os.environ.get("KAFKA_SECURITY_PROTOCOL", "SASL_SSL")
        conf["sasl.mechanisms"] = os.environ.get("KAFKA_SASL_MECHANISMS", "PLAIN")
        conf["sasl.username"] = args.username
        conf["sasl.password"] = args.password

    producer = Producer(conf)
    delivered = 0
    errors: list[str] = []

    def _cb(err, _msg):
        nonlocal delivered
        if err:
            errors.append(str(err))
        else:
            delivered += 1

    topic = args.topic
    now = datetime.now(timezone.utc).isoformat()
    for row in EVENTS:
        event_id = str(uuid.uuid4())
        payload = {
            "event_id": event_id,
            "invoice_id": row["invoice_id"],
            "customer_id": row["customer_id"],
            "booked_amount": row["booked_amount"],
            "event_ts": now,
            "source_topic": topic,
        }
        producer.produce(topic, json.dumps(payload).encode("utf-8"), callback=_cb)
        producer.poll(0)

    producer.flush(30)
    if errors:
        print("delivery errors:\n" + "\n".join(errors), file=sys.stderr)
    print(f"produced {delivered}/{len(EVENTS)} events to {topic}")
    return 0 if delivered == len(EVENTS) else 2


if __name__ == "__main__":
    raise SystemExit(main())
