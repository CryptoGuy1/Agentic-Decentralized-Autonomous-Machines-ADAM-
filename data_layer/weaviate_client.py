# data_layer/weaviate_client.py
"""
Robust Weaviate client shim that supports both v4 and legacy v3 clients.
Handles schema creation, insertion, and querying.

Designed to be defensive about client/library/server version differences.
"""

import os
import time
import atexit
from datetime import datetime, timezone
from typing import Any, List, Dict, Optional

WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
SENSOR_CLASS = "SensorEvent"

# module-level cached client and type marker
_client: Optional[Any] = None
_client_type: str = "unknown"


# -----------------------
# Client connection helpers

def _connect_v4(url: str):
    """Try to construct a v4 WeaviateClient in several common ways."""
    try:
        from weaviate import WeaviateClient
    except Exception as e:
        raise RuntimeError("Weaviate v4 client not available") from e

    # Try common constructor signatures
    for attempt in (
        lambda: WeaviateClient(url=url),
        lambda: WeaviateClient(url),
        lambda: WeaviateClient(),  # last resort
    ):
        try:
            return attempt()
        except TypeError:
            continue
        except Exception:
            continue
    raise RuntimeError("Could not instantiate WeaviateClient (v4) with known signatures.")


def _connect_v3(url: str):
    """
    Prefer a simple connect_to_local(skip_init_checks=True) call to avoid gRPC health checks.
    Fallback to legacy Client(url) if present.
    """
    import weaviate

    # 1) Prefer connect_to_local(skip_init_checks=True) which avoids blocking gRPC health checks
    if hasattr(weaviate, "connect_to_local"):
        try:
            # skip_init_checks avoids the client doing the gRPC ping at startup
            return weaviate.connect_to_local(skip_init_checks=True)
        except TypeError:
            # some older builds accept a different kwarg shape
            try:
                return weaviate.connect_to_local()
            except Exception:
                pass
        except Exception:
            pass

    # 2) Try legacy constructor Client(url) (positional or kw)
    if hasattr(weaviate, "Client"):
        try:
            return weaviate.Client(url)
        except TypeError:
            try:
                return weaviate.Client(url=url)
            except Exception:
                pass
    raise RuntimeError("No supported v3 connect method found.")


def get_client():
    """
    Return a connected Weaviate client (v4 preferred). Be defensive: try v3 skip-init, then v4, then REST-only shim.
    """
    global _client, _client_type
    if _client is not None:
        return _client

    # 0) Quick REST-only shim fallback factory (if everything else fails)
    def _rest_only_client():
        class RestOnly:
            def __init__(self, base_url):
                self._base = base_url.rstrip("/")

            # minimal helper used by your code: create, schema.get, objects list
            def schema_get(self):
                import requests
                r = requests.get(self._base + "/v1/schema", timeout=5)
                r.raise_for_status()
                return r.json()

            # keep attributes used by ensure_schema() and others as no-op wrappers
            def __getattr__(self, name):
                raise AttributeError("RestOnly client does not implement: " + name)

        return RestOnly(WEAVIATE_URL)

    # Try v3 skip-init (fast, avoids grpc checks)
    try:
        print(f"🔌 Trying legacy connect_to_local(skip_init_checks=True) -> {WEAVIATE_URL}")
        c = _connect_v3(WEAVIATE_URL)
        _client = c
        _client_type = "v3"
        print("✅ Connected using legacy v3 client (skip_init_checks preferred).")
        return _client
    except Exception as e_v3:
        print("⚠️ v3 skip-init attempt failed:", e_v3)

    # Try v4 client constructors
    try:
        print(f"🔌 Attempting Weaviate v4 connect -> {WEAVIATE_URL}")
        c = _connect_v4(WEAVIATE_URL)
        _client = c
        _client_type = "v4"
        print("✅ Connected using Weaviate v4 client.")
        return _client
    except Exception as e_v4:
        print("⚠️ v4 connection failed, falling back to REST-only client:", e_v4)

    # As a last resort provide a REST-only shim so your REST fallback code still works
    try:
        print("🔌 Creating REST-only fallback client (will use direct HTTP calls).")
        _client = _rest_only_client()
        _client_type = "rest-only"
        return _client
    except Exception as e:
        raise RuntimeError(f"Unable to create any Weaviate client for {WEAVIATE_URL}: {e}") from e


# Ensure client closed on exit to avoid ResourceWarning
def close_client():
    global _client
    try:
        if _client is not None and hasattr(_client, "close"):
            try:
                _client.close()
            except Exception:
                # ignore close errors
                pass
    finally:
        _client = None


atexit.register(close_client)


# -----------------------
# Schema setup
# -----------------------
def ensure_schema():
    """Ensure SensorEvent collection/class exists in Weaviate schema."""
    client = get_client()

    # prefer v4 schema API if available
    try:
        if _client_type == "v4" and hasattr(client, "schema"):
            schema = client.schema.get()
            classes = schema.get("classes", []) if isinstance(schema, dict) else []
            if any(c.get("class") == SENSOR_CLASS for c in classes):
                print("✅ Weaviate collection already exists.")
                return

            cls = {
                "class": SENSOR_CLASS,
                "description": "Methane sensor events",
                "properties": [
                    {"name": "timestamp", "dataType": ["date"]},
                    {"name": "node_id", "dataType": ["text"]},
                    {"name": "methane_ppm", "dataType": ["number"]},
                    {"name": "scenario", "dataType": ["text"]},
                    {"name": "trace_id", "dataType": ["text"]},
                ],
                # `vectorizer` optional; leave default unless you have a module configured
            }
            client.schema.create_class(cls)
            time.sleep(0.2)
            print("✅ Weaviate v4 collection created successfully.")
            return
    except Exception as e:
        print("❌ Failed to ensure schema (v4 path):", e)
        # fall through to try v3 or raise below

    # fallback attempt using older v3-style schema API
    try:
        # some legacy clients also expose schema.* – try same pattern
        if hasattr(client, "schema") and hasattr(client.schema, "get"):
            schema = client.schema.get()
            classes = schema.get("classes", []) if isinstance(schema, dict) else []
            if any(c.get("class") == SENSOR_CLASS for c in classes):
                print("✅ Weaviate collection already exists (v3 path).")
                return

            cls = {
                "class": SENSOR_CLASS,
                "description": "Methane sensor events",
                "properties": [
                    {"name": "timestamp", "dataType": ["date"]},
                    {"name": "node_id", "dataType": ["text"]},
                    {"name": "methane_ppm", "dataType": ["number"]},
                    {"name": "scenario", "dataType": ["text"]},
                    {"name": "trace_id", "dataType": ["text"]},
                ],
            }
            client.schema.create_class(cls)
            print("✅ Weaviate collection created (v3 fallback).")
            return
    except Exception as e:
        print("❌ Schema creation failed (v3 path):", e)
        raise


# -----------------------
# Insert and Query
# -----------------------
def insert_sensor_event(
    node_id: str,
    methane_ppm: float,
    scenario: str = "normal",
    trace_id: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> str:
    """Insert a methane reading into Weaviate. Returns trace_id."""
    client = get_client()
    if trace_id is None:
        trace_id = f"trace-{int(datetime.now(tz=timezone.utc).timestamp() * 1000)}"
    if timestamp is None:
        timestamp = datetime.now(tz=timezone.utc).isoformat()

    obj = {
        "timestamp": timestamp,
        "node_id": node_id,
        "methane_ppm": float(methane_ppm),
        "scenario": scenario,
        "trace_id": trace_id,
    }

    print("📤 Inserting object into Weaviate:", obj)

    # Try v4 data API first
    try:
        if _client_type == "v4":
            # new v4 client often supports client.data.create(data_object=..., class_name=...)
            if hasattr(client, "data") and hasattr(client.data, "create"):
                client.data.create(data_object=obj, class_name=SENSOR_CLASS)
                print("✅ Inserted via v4 data API.")
                return trace_id

            # some v4 variants use collections API
            if hasattr(client, "collections") and hasattr(client.collections, "get"):
                coll = client.collections.get(SENSOR_CLASS)
                coll.data.insert(obj)
                print("✅ Inserted via v4 collections API.")
                return trace_id
    except Exception as e:
        print("⚠️ v4 insert attempt failed, trying fallback:", e)

    # v3 fallback
    try:
        if hasattr(client, "data_object"):
            client.data_object.create(obj, SENSOR_CLASS)
            print("✅ Inserted via v3 data_object API.")
            return trace_id
    except Exception as e:
        print("⚠️ v3 insert failed:", e)
        raise RuntimeError("All insert attempts failed.") from e

    raise RuntimeError("No supported insert method found on Weaviate client.")


def get_recent_readings(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch recent sensor readings from Weaviate.
    Robust: tries v4 query, v4 collections, v3 query, and finally a REST fallback.
    Returns list[dict] or [].
    """
    client = get_client()

    # 1) v4 query path (client.query.get(...).with_limit(n).do())
    try:
        if _client_type == "v4" and hasattr(client, "query"):
            q = client.query.get(
                SENSOR_CLASS,
                ["timestamp", "node_id", "methane_ppm", "scenario", "trace_id"]
            ).with_limit(limit)
            res = q.do()
            if isinstance(res, dict):
                return res.get("data", {}).get("Get", {}).get(SENSOR_CLASS, [])
    except Exception as e:
        print("⚠️ v4 query failed:", e)

    # 2) v4 collections fetch_objects path
    try:
        if _client_type == "v4" and hasattr(client, "collections"):
            coll = client.collections.get(SENSOR_CLASS)
            result = coll.query.fetch_objects(limit=limit)
            return [obj.properties for obj in result.objects]
    except Exception as e:
        print("⚠️ v4 collections query failed:", e)

    # 3) v3 query fallback (older client)
    try:
        if hasattr(client, "query"):
            q = client.query.get(
                SENSOR_CLASS,
                ["timestamp", "node_id", "methane_ppm", "scenario", "trace_id"]
            ).with_limit(limit)
            res = q.do()
            if isinstance(res, dict):
                return res.get("data", {}).get("Get", {}).get(SENSOR_CLASS, [])
    except Exception as e:
        print("⚠️ v3 query failed:", e)

    # 4) REST fallback: directly call the Weaviate REST API
    try:
        import requests
        url = WEAVIATE_URL.rstrip("/") + f"/v1/objects?class={SENSOR_CLASS}&limit={limit}"
        # Note: some Weaviate installations require authentication; adapt if you use a token.
        r = requests.get(url, timeout=6)
        r.raise_for_status()
        j = r.json()
        # v1/objects returns {"objects":[{...}]}
        objs = j.get("objects") or j.get("results") or []
        out = []
        for o in objs:
            # object properties may be in `properties` or top-level
            props = o.get("properties") if isinstance(o, dict) else None
            if not props and isinstance(o, dict):
                # older shape: maybe properties at o["object"]["properties"]
                props = o.get("object", {}).get("properties") or o
            if props:
                out.append(props)
        if out:
            print("✅ Fetched readings using REST fallback.")
            return out
    except Exception as e:
        print("⚠️ REST fallback failed:", e)

    print("❌ Unable to query readings (no valid query method found).")
    return []
