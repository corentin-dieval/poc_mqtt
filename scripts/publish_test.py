import asyncio
import json
import uuid
from datetime import datetime, UTC, timedelta
import time
import random
import os
import sys

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
    MQTT_TOPIC = settings.MQTT_TOPIC
    print(f"Loaded MQTT settings from app.core.config: Host={MQTT_BROKER_HOST}, Port={MQTT_BROKER_PORT}, Topic={MQTT_TOPIC}")
except ImportError:
    print("Could not import app.core.config. Falling back to environment variables or hardcoded defaults.")
    MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
    MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))
    MQTT_TOPIC = os.getenv("MQTT_TOPIC", "machines/events")
    print(f"Using MQTT settings from environment variables/defaults: Host={MQTT_BROKER_HOST}, Port={MQTT_BROKER_PORT}, Topic={MQTT_TOPIC}")


# --- Simulation Configuration ---
NUM_CELLS_TO_SIMULATE = 2 # This means 2 * 2 = 4 initial stacks
DELAY_BETWEEN_EVENTS_SECONDS = 0.1
SIMULATE_NG_CHANCE = 0.1 # 10% chance for an NG status at any step

WORKCENTERS_SEQUENCE_PHASES = {
    "stacks_individual": [
        "stacking 1", "stacking 2", "stacking 3", "stacking 4", "stacking 5",
        "stacking 6", "stacking 7", "stacking 8", "stacking 9", "stacking 10",
        "stacking 11", "stacking 12",
        "ct scan SEC",
        "matching",
    ],
    "pairing_collector_welding": "collector welding",
    "paired_stacks_folding": "first folding",
    "cell_formation_cover_welding": "cover welding",
    "cells_final_assembly": [
        "mylar wrapping",
        "can insertion",
        "can welding",
        "first leak test",
        "ct scan zeiss"
    ]
}

# --- MQTT Client setup ---
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

def on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        print(f"Connected to MQTT Broker: {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
    else:
        print(f"Failed to connect, return code {rc}. Check broker address and port.\n")
        sys.exit(1)

# Corrected on_disconnect signature for CallbackAPIVersion.VERSION2
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
    """Helper function to publish a payload and log the result."""
    payload_json = json.dumps(payload)
    result = client.publish(MQTT_TOPIC, payload_json)
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print(f"  Published: {payload['id_product']} @ {payload['plm_workcenter']} -> {payload['status']}")
    else:
        print(f"  Failed to publish message for {payload['id_product']} @ {payload['plm_workcenter']}. Error code: {result.rc}")

async def simulate_product_journey():
    print(f"Starting simulation for {NUM_CELLS_TO_SIMULATE} cells (requiring {NUM_CELLS_TO_SIMULATE * 2} initial stacks)...")
    
    current_time = datetime.now(UTC)
    
    # Initialize individual stacks
    individual_stacks_ids = []
    for i in range(1, (NUM_CELLS_TO_SIMULATE * 2) + 1):
        individual_stacks_ids.append(f"STACK_{i:03d}")
    
    # Data structure to track units through phases
    # Each unit will have: id (stack_id or cell_id), type (STACK/CELL), status, last_event_time
    # For paired stacks/cells, it will also have 'stack_ids'
    
    # Phase 1: Individual Stacks (up to 'matching')
    print("\n--- Phase 1: Individual Stacks (up to 'matching') ---")
    
    active_stacks_data = [{"id": stack_id, "status": "OK", "last_event_time": current_time} for stack_id in individual_stacks_ids]
    
    for workcenter in WORKCENTERS_SEQUENCE_PHASES["stacks_individual"]:
        print(f"\nProcessing workcenter: {workcenter}")
        for stack_data in active_stacks_data:
            current_time += timedelta(seconds=random.uniform(DELAY_BETWEEN_EVENTS_SECONDS, DELAY_BETWEEN_EVENTS_SECONDS * 2))
            status = "NG" if random.random() < SIMULATE_NG_CHANCE else "OK"
            stack_data["status"] = status # Update stack's status
            stack_data["last_event_time"] = current_time

            payload = generate_event_payload(
                id_product=stack_data["id"],
                plm_workcenter=workcenter,
                status=status,
                timestamp=current_time,
                ipc_source_hostname=f"host-{workcenter.replace(' ', '-')}",
                plm_workunit=f"unit-{workcenter.replace(' ', '-')}",
            )
            await publish_payload(payload)
            await asyncio.sleep(DELAY_BETWEEN_EVENTS_SECONDS)

    # Phase 2: Pairing at Collector Welding
    print(f"\n--- Phase 2: Pairing at '{WORKCENTERS_SEQUENCE_PHASES['pairing_collector_welding']}' ---")
    
    paired_stacks_data = [] # List of {"stack_ids": [s1, s2], "status": "OK/NG", "last_event_time": time}
    
    # Pair up stacks
    for i in range(0, len(active_stacks_data), 2):
        stack1_data = active_stacks_data[i]
        stack2_data = active_stacks_data[i+1]
        
        # The status of the pair is NG if any of the stacks were NG
        pair_status = "NG" if stack1_data["status"] == "NG" or stack2_data["status"] == "NG" else "OK"
        
        # Send events for both stacks at collector welding
        workcenter = WORKCENTERS_SEQUENCE_PHASES["pairing_collector_welding"]
        
        # Event for stack 1
        current_time += timedelta(seconds=random.uniform(DELAY_BETWEEN_EVENTS_SECONDS, DELAY_BETWEEN_EVENTS_SECONDS * 2))
        payload1 = generate_event_payload(
            id_product=stack1_data["id"],
            plm_workcenter=workcenter,
            status=pair_status, # Status of the pair
            timestamp=current_time,
            ipc_source_hostname=f"host-{workcenter.replace(' ', '-')}",
            plm_workunit=f"unit-{workcenter.replace(' ', '-')}",
        )
        await publish_payload(payload1)
        await asyncio.sleep(DELAY_BETWEEN_EVENTS_SECONDS)

        # Event for stack 2
        current_time += timedelta(seconds=random.uniform(DELAY_BETWEEN_EVENTS_SECONDS, DELAY_BETWEEN_EVENTS_SECONDS * 2))
        payload2 = generate_event_payload(
            id_product=stack2_data["id"],
            plm_workcenter=workcenter,
            status=pair_status, # Status of the pair
            timestamp=current_time,
            ipc_source_hostname=f"host-{workcenter.replace(' ', '-')}",
            plm_workunit=f"unit-{workcenter.replace(' ', '-')}",
        )
        await publish_payload(payload2)
        await asyncio.sleep(DELAY_BETWEEN_EVENTS_SECONDS)
        
        paired_stacks_data.append({
            "stack_ids": [stack1_data["id"], stack2_data["id"]],
            "status": pair_status,
            "last_event_time": current_time # Use the latest time of the two events
        })
    
    # Phase 3: Paired Stacks (First Folding)
    print(f"\n--- Phase 3: Paired Stacks at '{WORKCENTERS_SEQUENCE_PHASES['paired_stacks_folding']}' ---")
    workcenter = WORKCENTERS_SEQUENCE_PHASES["paired_stacks_folding"]
    
    for unit_pair in paired_stacks_data:
        # Send events for both stacks in the pair
        for stack_id in unit_pair["stack_ids"]:
            current_time += timedelta(seconds=random.uniform(DELAY_BETWEEN_EVENTS_SECONDS, DELAY_BETWEEN_EVENTS_SECONDS * 2))
            status = "NG" if random.random() < SIMULATE_NG_CHANCE else "OK" # New status for this step
            unit_pair["status"] = "NG" if status == "NG" or unit_pair["status"] == "NG" else "OK" # Propagate NG
            unit_pair["last_event_time"] = current_time

            payload = generate_event_payload(
                id_product=stack_id, # Still using stack ID
                plm_workcenter=workcenter,
                status=status,
                timestamp=current_time,
                ipc_source_hostname=f"host-{workcenter.replace(' ', '-')}",
                plm_workunit=f"unit-{workcenter.replace(' ', '-')}",
            )
            await publish_payload(payload)
            await asyncio.sleep(DELAY_BETWEEN_EVENTS_SECONDS)

    # Phase 4: Cell Formation at Cover Welding
    print(f"\n--- Phase 4: Cell Formation at '{WORKCENTERS_SEQUENCE_PHASES['cell_formation_cover_welding']}' ---")
    
    active_cells_data = [] # List of {"id": "CELL_XXX", "status": "OK/NG", "last_event_time": time, "stack_ids": [s1, s2]}
    
    workcenter = WORKCENTERS_SEQUENCE_PHASES["cell_formation_cover_welding"]
    
    for i, unit_pair in enumerate(paired_stacks_data):
        cell_id = f"CELL_{i+1:04d}" # Generate new cell ID
        
        current_time += timedelta(seconds=random.uniform(DELAY_BETWEEN_EVENTS_SECONDS, DELAY_BETWEEN_EVENTS_SECONDS * 2))
        status = "NG" if random.random() < SIMULATE_NG_CHANCE else "OK" # New status for this step
        final_cell_status = "NG" if status == "NG" or unit_pair["status"] == "NG" else "OK" # Propagate NG from stacks
        
        payload = generate_event_payload(
            id_product=cell_id,
            plm_workcenter=workcenter,
            status=final_cell_status,
            timestamp=current_time,
            ipc_source_hostname=f"host-{workcenter.replace(' ', '-')}",
            plm_workunit=f"unit-{workcenter.replace(' ', '-')}",
        )
        await publish_payload(payload)
        await asyncio.sleep(DELAY_BETWEEN_EVENTS_SECONDS)
        
        active_cells_data.append({
            "id": cell_id,
            "status": final_cell_status,
            "last_event_time": current_time,
            "stack_ids": unit_pair["stack_ids"]
        })
        print(f"  Formed {cell_id} from {unit_pair['stack_ids'][0]} and {unit_pair['stack_ids'][1]} with status {final_cell_status}")

    # Phase 5: Cells Final Assembly
    print(f"\n--- Phase 5: Cells Final Assembly (post 'cover welding') ---")
    
    for workcenter in WORKCENTERS_SEQUENCE_PHASES["cells_final_assembly"]:
        print(f"\nProcessing workcenter: {workcenter}")
        for cell_unit in active_cells_data:
            current_time += timedelta(seconds=random.uniform(DELAY_BETWEEN_EVENTS_SECONDS, DELAY_BETWEEN_EVENTS_SECONDS * 2))
            status = "NG" if random.random() < SIMULATE_NG_CHANCE else "OK" # New status for this step
            cell_unit["status"] = "NG" if status == "NG" or cell_unit["status"] == "NG" else "OK" # Propagate NG
            cell_unit["last_event_time"] = current_time

            payload = generate_event_payload(
                id_product=cell_unit["id"],
                plm_workcenter=workcenter,
                status=status,
                timestamp=current_time,
                ipc_source_hostname=f"host-{workcenter.replace(' ', '-')}",
                plm_workunit=f"unit-{workcenter.replace(' ', '-')}",
            )
            await publish_payload(payload)
            await asyncio.sleep(DELAY_BETWEEN_EVENTS_SECONDS)

    print("\nSimulation finished.")

if __name__ == "__main__":
    try:
        asyncio.run(simulate_product_journey())
    except KeyboardInterrupt:
        print("\nSimulation interrupted by user.")
    finally:
        client.loop_stop()
        client.disconnect()
        print("MQTT client disconnected.")
