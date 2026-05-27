import asyncio
import json
import uuid
from datetime import datetime, UTC, timedelta
import time
import random
import os
import sys
import string

import paho.mqtt.client as mqtt

# Attempt to load settings from the application's config
try:
    # Add project root to sys.path to allow importing app modules
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    from app.core.config import settings
    MQTT_BROKER_HOST = settings.MQTT_BROKER_HOST
    MQTT_BROKER_PORT = settings.MQTT_BROKER_PORT
    print(f"Loaded MQTT settings from app.core.config: Host={MQTT_BROKER_HOST}, Port={MQTT_BROKER_PORT}")
except ImportError:
    print("Could not import app.core.config. Falling back to environment variables or hardcoded defaults.")
    MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
    MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))
    print(f"Using MQTT settings from environment variables/defaults: Host={MQTT_BROKER_HOST}, Port={MQTT_BROKER_PORT}")


# --- Simulation Configuration ---
MIN_DELAY_BETWEEN_EVENTS_SECONDS = 0.5
MAX_DELAY_BETWEEN_EVENTS_SECONDS = 2.0
SIMULATE_NG_CHANCE = 0.1 # 10% chance for an NG status

# List of all possible workcenters from the original simulation script
ALL_WORKCENTERS = [
    "stacking 1", "stacking 2", "stacking 3", "stacking 4", "stacking 5",
    "stacking 6", "stacking 7", "stacking 8", "stacking 9", "stacking 10",
    "stacking 11", "stacking 12",
    "ct scan SEC",
    "matching",
    "collector welding",
    "first folding",
    "cover welding",
    "mylar wrapping",
    "can insertion",
    "can welding",
    "first leak test",
    "ct scan zeiss"
]

# --- MQTT Client setup ---
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

def on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        print(f"Connected to MQTT Broker: {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
    else:
        print(f"Failed to connect, return code {rc}. Check broker address and port.\n")
        sys.exit(1)

def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    print(f"DEBUG: on_disconnect called with disconnect_flags={disconnect_flags}, reason_code={reason_code}")
    print(f"Disconnected from MQTT Broker with code {reason_code}")

client.on_connect = on_connect
client.on_disconnect = on_disconnect

try:
    client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
except Exception as e:
    print(f"Error connecting to MQTT broker: {e}")
    sys.exit(1)

client.loop_start() # Start background thread for MQTT network loop

# --- Helper for random ID generation ---
def generate_random_id(length: int = 18) -> str:
    """Generates a random alphanumeric string of specified length."""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

# --- Event Generation ---
def generate_event_payload(
    id_product: str,
    plm_workcenter: str,
    status: str,
    timestamp: datetime,
    ipc_source_hostname: str,
    plm_workunit: str,
) -> dict:
    """Generates a single MQTT event payload."""
    return {
        "event_id": str(uuid.uuid4()),
        "id_product": id_product,
        "ipc_source_hostname": ipc_source_hostname,
        "plm_workcenter": plm_workcenter,
        "plm_workunit": plm_workunit,
        "machine_id": plm_workcenter.replace(" ", "_").lower(), # Simple machine_id
        "timestamp": timestamp.isoformat(),
        "status": status,
    }

async def publish_payload(payload: dict):
    """Helper function to publish a payload to a machine-specific topic and log the result."""
    machine_id = payload.get("machine_id", "unknown")
    dynamic_topic = f"machines/{machine_id}/events" # Construct topic dynamically
    payload_json = json.dumps(payload)
    result = client.publish(dynamic_topic, payload_json) # Publish to dynamic topic
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print(f"  Published to '{dynamic_topic}': {payload['id_product']} @ {payload['plm_workcenter']} -> {payload['status']}")
    else:
        print(f"  Failed to publish message for {payload['id_product']} @ {payload['plm_workcenter']} to '{dynamic_topic}'. Error code: {result.rc}")

async def live_simulate_events():
    print("Starting live event simulation. Press Ctrl+C to stop.")
    while True:
        current_time = datetime.now(UTC)
        
        # Randomly pick a workcenter
        plm_workcenter = random.choice(ALL_WORKCENTERS)
        
        # Generate a new random product ID for each event
        id_product = generate_random_id()
        
        # Randomly assign status
        status = "NG" if random.random() < SIMULATE_NG_CHANCE else "OK"
        
        # Generate hostname and workunit based on workcenter
        ipc_source_hostname = f"host-{plm_workcenter.replace(' ', '-')}"
        plm_workunit = f"unit-{plm_workcenter.replace(' ', '-')}"

        payload = generate_event_payload(
            id_product=id_product,
            plm_workcenter=plm_workcenter,
            status=status,
            timestamp=current_time,
            ipc_source_hostname=ipc_source_hostname,
            plm_workunit=plm_workunit,
        )
        await publish_payload(payload)
        
        # Wait for a random delay before the next event
        await asyncio.sleep(random.uniform(MIN_DELAY_BETWEEN_EVENTS_SECONDS, MAX_DELAY_BETWEEN_EVENTS_SECONDS))

if __name__ == "__main__":
    try:
        asyncio.run(live_simulate_events())
    except KeyboardInterrupt:
        print("\nLive simulation interrupted by user.")
    finally:
        client.loop_stop()
        client.disconnect()
        print("MQTT client disconnected.")
