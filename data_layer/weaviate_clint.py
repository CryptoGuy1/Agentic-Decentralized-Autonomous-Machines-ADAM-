# autonomous/weaviate_client.py
import weaviate
import os
from datetime import datetime, timezone
from typing import List, Dict, Any

WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")

SENSOR_CLASS = "SensorEvent"


def get_client():
    """Return a weaviate client, attempting v4 helper first then falling back.

    This function keeps imports and usage tolerant across different installed
    weaviate client versions.
    """
    # Try newer connect helper
    try:
        connect = getattr(weaviate, "connect_to_local", None)
        if callable(connect):
            return connect(skip_init_checks=True)
    except Exception:
        pass

    # Fallback to explicit Client constructor
    try:
        return weaviate.Client(WEAVIATE_URL)
    except Exception:
        # Last resort: try connect (older versions)
        try:
            return weaviate.connect(WEAVIATE_URL)
        except Exception as e:
            raise RuntimeError("Unable to create Weaviate client") from e


# single shared client instance for module
client = get_client()


def ensure_schema():
    """Ensure the SensorEvent class exists in Weaviate.

    Works with either v3 (schema) or v4 (collections/classes) client APIs.
    """
    from weaviate.classes.config import Property, DataType

# ... inside ensure_schema(), replace the try block with:
    try:
        from weaviate.classes.config import Property, DataType

        properties = [
            Property(name="timestamp", data_type=DataType.DATE, description="Reading time"),
            Property(name="node_id", data_type=DataType.TEXT, description="Sensor node ID"),
            Property(name="methane_ppm", data_type=DataType.NUMBER, description="Methane level (ppm)"),
            Property(name="scenario", data_type=DataType.TEXT, description="Scenario or condition"),
            Property(name="trace_id", data_type=DataType.TEXT, description="Trace reference"),
        ]

        client.collections.create(
            name=SENSOR_CLASS,
            description="Methane sensor events",
            properties=properties,
        )
        print("✅ Weaviate v4 collection created successfully.")
        
    except Exception as e:
        print("❌ Unable to create collection via v4 API:", e)


        # --- v4-style API ---
        if hasattr(client, "collections"):
            try:
                existing = client.collections.list_all()
            except Exception:
                existing = []

            # Normalize to names (handles both string and object results)
            existing_names = []
            for c in existing:
                if isinstance(c, str):
                    existing_names.append(c)
                elif hasattr(c, "name"):
                    existing_names.append(c.name)

            if SENSOR_CLASS not in existing_names:
                try:
                    client.collections.create(
                        name=SENSOR_CLASS,
                        description="Methane sensor events",
                        properties=[
                            {"name": "timestamp", "dataType": ["date"]},
                            {"name": "node_id", "dataType": ["text"]},
                            {"name": "methane_ppm", "dataType": ["number"]},
                            {"name": "scenario", "dataType": ["text"]},
                            {"name": "trace_id", "dataType": ["text"]}
                        ],
                    )
                    print("✅ Weaviate v4 collection created.")
                except Exception as e:
                    print("❌ Unable to create collection via v4 API:", e)
            else:
                print("✅ Weaviate v4 collection already exists.")
            return

        print("⚠️ Unable to determine Weaviate client API for schema creation.")

    except Exception as e:
        print("❌ Error while ensuring schema:", e)



def insert_sensor_event(
    node_id: str,
    methane_ppm: float,
    scenario: str = "",
    trace_id: str = None,
    timestamp: str = None
):
    if trace_id is None:
        trace_id = f"trace-{int(datetime.now(tz=timezone.utc).timestamp()*1000)}"
    if timestamp is None:
        timestamp = datetime.now(tz=timezone.utc).isoformat()
    obj = {
        "timestamp": timestamp,
        "node_id": node_id,
        "methane_ppm": methane_ppm,
        "scenario": scenario,
        "trace_id": trace_id
    }

    # Try v3-style insert
    try:
        if hasattr(client, "data_object"):
            client.data_object.create(obj, SENSOR_CLASS)
            return trace_id
    except Exception:
        pass
    # Try v4-style insert
    try:
        if hasattr(client, "data_objects"):
            # some v4 helpers expose data_objects.create
            client.data_objects.create(obj, SENSOR_CLASS)
            return trace_id
    except Exception:
        pass

    # Last resort: try a raw REST call via client
    try:
        if hasattr(client, "connection"):
            client.connection.post("/v1/objects", json={"class": SENSOR_CLASS, "properties": obj})
            return trace_id
    except Exception as e:
        raise RuntimeError("Failed to insert object into Weaviate") from e


def query_recent_events(node_id=None, minutes=5, limit=10) -> Dict[str, Any]:
    # Basic GraphQL query to get recent events (pre-filter)
    q = {
        "query": f"""{{
          Get {{
            {SENSOR_CLASS}(limit: {limit}) {{
              node_id
              methane_ppm
              timestamp
              trace_id
            }}
          }}
        }}"""
    }
    try:
        if hasattr(client, "query") and hasattr(client.query, "raw"):
            res = client.query.raw(q["query"])
            return res
    except Exception:
        pass
    # fallback: try low-level REST call
    try:
        if hasattr(client, "connection"):
            r = client.connection.post("/v1/graphql", json={"query": q["query"]})
            return r.json()
    except Exception as e:
        raise RuntimeError("Failed to query Weaviate") from e


def get_recent_readings(limit: int = 10) -> List[Dict[str, Any]]:
    """Return a list of recent sensor readings as simple dicts.

    This parses GraphQL results into a compact list for downstream use.
    """
    res = query_recent_events(limit=limit)
    try:
        data = res.get("data", {}).get("Get", {}).get(SENSOR_CLASS, [])
        # If structure differs, attempt to extract directly
        if not data and isinstance(res, dict):
            # some clients return {'Get': {SENSOR_CLASS: [...]}}
            get_block = res.get("Get") or res.get("data")
            if get_block and SENSOR_CLASS in get_block:
                data = get_block[SENSOR_CLASS]
        return data or []
    except Exception:
        return []
