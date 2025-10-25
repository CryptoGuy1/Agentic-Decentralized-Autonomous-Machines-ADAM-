# autonomous/api_server.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime
from typing import Dict, Any
import traceback
from data_layer.weaviate_client import get_recent_readings


# ✅ Import your existing Weaviate insert function
from data_layer.weaviate_client import insert_sensor_event

app = FastAPI(title="Methane Sensor API", version="1.0")


@app.post("/sensor-data")
async def receive_sensor_data(request: Request):
    """
    Receives methane sensor readings from Node-RED and inserts them into Weaviate.
    Expected JSON body:
    {
        "timestamp": "2025-10-22T20:40:00Z",
        "node_id": "Sensor_A",
        "methane_ppm": 15.3,
        "scenario": "normal"
    }
    """
    try:
        data: Dict[str, Any] = await request.json()

        # ✅ Basic validation
        required = ["timestamp", "node_id", "methane_ppm"]
        for key in required:
            if key not in data:
                return JSONResponse(
                    {"error": f"Missing required field: {key}"}, status_code=400
                )

        # Default values if not provided
        data.setdefault("scenario", "normal")
        data.setdefault("trace_id", f"trace-{datetime.utcnow().isoformat()}")

        # ✅ Insert into Weaviate
        insert_sensor_event(
            timestamp=data["timestamp"],
            node_id=data["node_id"],
            methane_ppm=data["methane_ppm"],
            scenario=data.get("scenario", "normal")
        )


        return JSONResponse(
            {"status": "ok", "message": "Sensor data received and stored", "data": data}
        )

    except Exception as e:
        print("Error:", e)
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/recent-readings")
async def recent_readings(limit: int = 10, node_id: str = None):
    """
    Returns recent sensor readings from Weaviate.
    Optional query parameters:
      - limit: number of readings to return (default 10)
      - node_id: filter readings from a specific sensor
    Example:
      /recent-readings?limit=5
      /recent-readings?node_id=Sensor_A&limit=3
    """
    try:
        # Fetch readings from Weaviate
        data = get_recent_readings(limit=limit)
        
        # Filter by node_id if provided
        if node_id:
            data = [item for item in data if item.get("node_id") == node_id]
        
        # Serialize datetime objects to strings
        serialized_data = []
        for item in data:
            item_copy = item.copy()
            if isinstance(item_copy.get("timestamp"), datetime):
                item_copy["timestamp"] = item_copy["timestamp"].isoformat()
            serialized_data.append(item_copy)

        return JSONResponse({"status": "ok", "count": len(serialized_data), "data": serialized_data})
    
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    

if __name__ == "__main__":
    # 🚀 Start FastAPI locally on port 8000
    uvicorn.run("autonomous.api_server:app", host="0.0.0.0", port=8000, reload=True)
