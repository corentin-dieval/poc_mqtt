#!/usr/bin/env python
"""
Script de test — publie des événements MQTT de test vers le broker.

Usage:
    uv run python scripts/publish_test.py
    MQTT_BROKER_HOST=localhost uv run python scripts/publish_test.py
"""

import json
import os
import time
import uuid
from datetime import UTC, datetime

import paho.mqtt.client as mqtt

BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
TOPIC = os.getenv("MQTT_TOPIC", "machines/events")

TEST_EVENTS = [
    {"machine_id": "MACHINE_01", "status": "OK"},
    {"machine_id": "MACHINE_02", "status": "NG"},
    {"machine_id": "MACHINE_01", "status": "OK"},
    {"machine_id": "MACHINE_03", "status": "OK"},
    {"machine_id": "MACHINE_02", "status": "NG"},
]


def build_payload(machine_id: str, status: str) -> dict:
    return {
        "event_id": str(uuid.uuid4()),
        "machine_id": machine_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "status": status,
    }


def main() -> None:
    client = mqtt.Client(
        client_id="poc-test-publisher",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )

    print(f"Connecting to MQTT broker at {BROKER_HOST}:{BROKER_PORT}…")
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    client.loop_start()

    time.sleep(0.5)  # wait for connection

    for event in TEST_EVENTS:
        payload = build_payload(event["machine_id"], event["status"])
        result = client.publish(TOPIC, json.dumps(payload), qos=1)
        result.wait_for_publish(timeout=5)
        print(f"  ✓ Published: {payload['machine_id']} [{payload['status']}] → {TOPIC}")
        time.sleep(0.2)

    client.loop_stop()
    client.disconnect()
    print(f"\nDone — {len(TEST_EVENTS)} events published.")


if __name__ == "__main__":
    main()

