# run/auto_cycle.py
import time
import requests
import traceback
from datetime import datetime
from autonomous.crew import MethaneMonitoringCrew

# Configuration
API_URL = "http://127.0.0.1:8000/recent-readings?limit=1"
CHECK_INTERVAL = 15  # seconds between checks
LAST_TIMESTAMP = None

def get_latest_timestamp():
    """Fetch latest sensor data timestamp from API."""
    try:
        resp = requests.get(API_URL, timeout=10)
        data = resp.json()
        if data["status"] == "ok" and data["count"] > 0:
            latest = data["data"][0]["timestamp"]
            return latest
        return None
    except Exception as e:
        print("❌ Error checking for new data:", e)
        traceback.print_exc()
        return None

def run_crew_cycle():
    """Run the methane monitoring crew once."""
    try:
        print("🚀 Running Crew automatically at", datetime.utcnow())
        crew_instance = MethaneMonitoringCrew()
        crew_instance.crew().kickoff(inputs={})
        print("✅ Crew completed successfully.")
    except Exception as e:
        print("❌ Crew run failed:", e)
        traceback.print_exc()

if __name__ == "__main__":
    print("🔄 Autonomous Crew Monitor started...")
    print(f"⏱️ Checking for new sensor data every {CHECK_INTERVAL} seconds...\n")

    global LAST_TIMESTAMP
    LAST_TIMESTAMP = get_latest_timestamp()

    while True:
        new_timestamp = get_latest_timestamp()

        if new_timestamp and new_timestamp != LAST_TIMESTAMP:
            print(f"\n🆕 New data detected at {new_timestamp} — running Crew!\n")
            run_crew_cycle()
            LAST_TIMESTAMP = new_timestamp
        else:
            print(f"⏳ No new data. Last seen timestamp: {LAST_TIMESTAMP}")

        time.sleep(CHECK_INTERVAL)
