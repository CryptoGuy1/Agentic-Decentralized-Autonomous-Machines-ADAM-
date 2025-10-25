# autonomous/weaviate_client.py
import weaviate
import os
from datetime import datetime, timezone
from typing import List, Dict, Any

WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
SENSOR_CLASS = "SensorEvent"


def get_client():
    """Connect to Weaviate (handles v3/v4 compatibility)."""
    try:
        if hasattr(weaviate, "connect_to_local"):
            return weaviate.connect_to_local(skip_init_checks=True)
    except Exception:
        pass

    try:
        return weaviate.Client(WEAVIATE_URL)
    except Exception as e:
        raise RuntimeError("Unable to connect to Weaviate") from e


client = get_client()


def ensure_schema():
    """Ensure SensorEvent collection exists in Weaviate."""
    from weaviate.classes.config import Property, DataType
    try:
        if hasattr(client, "collections"):
            existing = [c.name if hasattr(c, "name") else c for c in client.collections.list_all()]
            if SENSOR_CLASS not in existing:
                client.collections.create(
                    name=SENSOR_CLASS,
                    description="Methane sensor events",
                    properties=[
                        Property(name="timestamp", data_type=DataType.DATE),
                        Property(name="node_id", data_type=DataType.TEXT),
                        Property(name="methane_ppm", data_type=DataType.NUMBER),
                        Property(name="scenario", data_type=DataType.TEXT),
                        Property(name="trace_id", data_type=DataType.TEXT),
                    ],
                )
                print("✅ Created Weaviate collection:", SENSOR_CLASS)
            else:
                print("✅ Weaviate collection already exists.")
    except Exception as e:
        print("❌ Schema setup failed:", e)


def insert_sensor_event(
    node_id: str,
    methane_ppm: float,
    scenario: str = "normal",
    trace_id: str = None,
    timestamp: str = None
):
    """Insert one methane reading into Weaviate."""
    try:
        if trace_id is None:
            trace_id = f"trace-{int(datetime.now(tz=timezone.utc).timestamp()*1000)}"
        if timestamp is None:
            timestamp = datetime.now(tz=timezone.utc).isoformat()

        obj = {
            "timestamp": timestamp,
            "node_id": node_id,
            "methane_ppm": methane_ppm,
            "scenario": scenario,
            "trace_id": trace_id,
        }

        print("📤 Inserting object into Weaviate:", obj)

        # v4 insert path
        if hasattr(client, "collections"):
            collection = client.collections.get(SENSOR_CLASS)
            collection.data.insert(obj)
            print("✅ Inserted via v4 API.")
            return trace_id

        # fallback to v3 API
        if hasattr(client, "data_object"):
            client.data_object.create(obj, SENSOR_CLASS)
            print("✅ Inserted via v3 API.")
            return trace_id

        raise RuntimeError("No valid insert API found for client.")

    except Exception as e:
        print("❌ Failed to insert object:", e)
        raise


def query_recent_events(limit: int = 10) -> List[Dict[str, Any]]:
    """Fetch recent events."""
    try:
        if hasattr(client, "collections"):
            collection = client.collections.get(SENSOR_CLASS)
            results = collection.query.fetch_objects(limit=limit)
            return [obj.properties for obj in results.objects]
    except Exception as e:
        print("❌ Query failed:", e)
        return []


def get_recent_readings(limit: int = 10) -> List[Dict[str, Any]]:
    """Simple wrapper for the API."""
    return query_recent_events(limit=limit)
