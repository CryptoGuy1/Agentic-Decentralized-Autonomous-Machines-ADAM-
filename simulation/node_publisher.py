# node_publisher.py
import requests
import json
from datetime import datetime
import random

NODE_RED_IN_URL = "http://localhost:1880/ingest"  # Node-RED HTTP In node

def publish_once(node_id="node_1"):
    payload = {
        "node_id": node_id,
        "methane_ppm": round(random.uniform(3.0, 9.0), 2),
        "timestamp": datetime.utcnow().isoformat()
    }
    r = requests.post(NODE_RED_IN_URL, json=payload, timeout=5)
    print("Published:", r.status_code, r.text)

if __name__ == "__main__":
    publish_once()

