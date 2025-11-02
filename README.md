# ADAM — (CrewAI + Weaviate + Node-RED)

**Purpose**  
This repository contains Veri-ADAM components to ingest methane sensor readings, store them in Weaviate, and run an autonomous CrewAI pipeline that validates, analyzes, and reports anomalies (with optional email alerts).  
This README guides a user with **no prior programming experience** to set up and run the project on **Windows PowerShell**.

---

## Table of contents

1. Quick summary  
2. What you need (software & accounts)  
3. Project layout  
4. Step-by-step installation (Windows PowerShell)  
5. Configure secrets (`.env`)  
6. Running Weaviate (Docker)  
7. Creating the Weaviate schema  
8. Start the FastAPI ingestion server  
9. Test ingestion with PowerShell  
10. Verify data in Weaviate  
11. Run the CrewAI pipeline  
12. Node-RED simulation (sensor flow)  
13. Useful PowerShell commands  
14. Troubleshooting (common fixes)  
15. Next steps & notes

---

## 1 — Quick summary

This system:
- Receives methane sensor data via HTTP (`/sensor-data`).
- Stores readings in **Weaviate**.
- Runs a **CrewAI workflow** to:
  - Validate readings  
  - Detect anomalies  
  - Send alerts and reports (email optional)

You can simulate data manually or through **Node-RED**.

---

## 2 — What you need

Install or ensure you have:
- **Windows 10 or 11 or MacBook**  
- **Python 3.12.x** 
- **Docker Desktop** (for Weaviate database)  
- **VS Code** (recommended editor)  
- **Node-RED** (for sensor data simulation)  
- **Gmail App Password** (for alert emails — optional)

---

### 3 — Project layout

- `methane_monitoring_ai/`
  - `autonomous/` — CREWAI / cognitive layer
    - `crew.py` — CrewAI orchestration (agents & tasks)
    - `reasoning_agent.py` — LLM reasoning and anomaly decision logic
    - `email_alert.py` — Gmail alert helper
    - `api_server.py` — FastAPI ingestion server (receives Node-RED or HTTP posts)
  - `data_layer/` — Vector DB schema and Weaviate utilities
    - `create_schema.py` — Create Weaviate `SensorEvent` class
    - `test_weaviate_connection.py` — Connection sanity checks
    - `weaviate_client.py` — Weaviate connection and CRUD helpers
    - `weaviate_utils.py` — Insert / query helper wrappers
  - `simulation/` — Simulators and Node-RED flow
    - `simulate_mq4.py` — Python methane sensor simulator
    - `node_publisher.py` — Publishes simulated data to Node-RED or API
    - `node_red_flow.json` — Node-RED flow import file
  - `config/` — YAML configuration
    - `agents.yaml`
    - `tasks.yaml`
    - `settings.yaml`
  - `run/` — Run & test utilities
    - `auto_cycle.py` — loop/watcher to trigger Crew periodically
    - `main.py`
    - `test_anomaly_cycle.py`
- `docker-compose.yml` — Weaviate and optional vectorizer containers
- `requirements.txt` — Python packages to install in `.venv`
- `README.md` — Project documentation
- `.env` — Local secrets (GMAIL creds, WEAVIATE_URL) — **do not commit**

---

## 4 — Step-by-step installation (Windows PowerShell)

> 🔹 Open PowerShell normally for setup commands  
> 🔹 Use Administrator PowerShell only for Docker install or virtualization setup

## Quick start — step-by-step (copy & paste)

### Step 1 — Clone or download the project
git clone <your-github-repo-url>
cd adams

### Step 2 — Create and activate a virtual environment
powershell
Copy code
python -m venv .venv
& ".\.venv\Scripts\Activate.ps1"
You’ll see (.venv) at the start of your prompt.

### Step 3 — Install dependencies
powershell
Copy code
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
⚠️ If you see:

yaml
Copy code
ERROR: No matching distribution found for smtplib
Remove smtplib from requirements.txt — smtplib is part of Python’s standard library.

5 — Configure .env file
Create a .env file at your project root with the following contents:

ini
Copy code
WEAVIATE_URL=http://localhost:8080
METHANE_THRESHOLD_PPM=80
GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password_here
Use a Gmail App Password, not your regular password. Generate one under: Google Account → Security → App Passwords.

6 — Run Weaviate (Docker)
Step 1 — Start Docker Desktop
Ensure virtualization (Intel VT-x or AMD-V) is enabled in your BIOS.

Step 2 — Launch Weaviate

powershell
Copy code
docker compose up -d
docker compose logs -f
Wait until you see: ✅ Weaviate is ready to receive requests

Check manually:

powershell
Copy code
Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/.well-known/ready"
If you get a JSON response → it's working.

7 — Create Weaviate schema
Run this command once:

powershell
Copy code
python -m data_layer.create_schema
Expected output:

Copy code
✅ Weaviate v4 collection created successfully.
or

arduino
Copy code
Collection already exists.
8 — Start the FastAPI ingestion server
This API receives methane readings and triggers the crew automatically.

powershell
Copy code
& ".\.venv\Scripts\Activate.ps1"
python -m autonomous.api_server
If successful, you’ll see:

makefile
Copy code
INFO:     Application startup complete.
API runs on: http://127.0.0.1:8000

9 — Test ingestion manually
Send test data from PowerShell:

powershell
Copy code
Invoke-RestMethod -Uri "http://127.0.0.1:8000/sensor-data" `
  -Method POST `
  -Headers @{ "Content-Type" = "application/json" } `
  -Body '{"timestamp":"2025-10-23T14:00:00Z","node_id":"CH4_001","methane_ppm":90.0}'
Expected response:

json
Copy code
{
  "status": "ok",
  "message": "Data stored, crew triggered",
  "data": { ... }
}
10 — Verify data in Weaviate
Method 1 — Via FastAPI
powershell
Copy code
$response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/recent-readings?limit=5"
$response | ConvertTo-Json -Depth 5
Method 2 — Directly via GraphQL
powershell
Copy code
$body = '{ "query": "{ Get { SensorEvent(limit:5) { node_id methane_ppm timestamp } } }" }'
Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/graphql" -Method POST -Body $body -ContentType "application/json"
You should see the sensor entries you just added.

11 — Run the CrewAI pipeline
Manual run
powershell
Copy code
python -m autonomous.crew
This runs: collect → validate → detect → report.

Automatic run (recommended)
The crew is already triggered automatically in api_server.py whenever new data arrives via /sensor-data.

Alternatively, run a loop watcher:

powershell
Copy code
python run/auto_cycle.py
This watches Weaviate for new data and triggers the CrewAI periodically.

12 — Node-RED simulation
Open Node-RED in your browser: http://127.0.0.1:1880.

Import → simulation/node_red_flow.json.

Deploy the flow.

Press the inject node to send data → Node-RED will post it to FastAPI.

Check your PowerShell terminal for Crew activity.

13 — Useful PowerShell commands
Activate venv:

powershell
Copy code
& ".\.venv\Scripts\Activate.ps1"
Start Weaviate:

powershell
Copy code
docker compose up -d
Create schema:

powershell
Copy code
python -m data_layer.create_schema
Start API:

powershell
Copy code
python -m autonomous.api_server
Send test data:

powershell
Copy code
Invoke-RestMethod -Uri "http://127.0.0.1:8000/sensor-data" -Method POST -Headers @{ "Content-Type" = "application/json" } -Body '{"timestamp":"2025-10-23T14:00:00Z","node_id":"CH4_001","methane_ppm":90.0}'
Run crew manually:

powershell
Copy code
python -m autonomous.crew
Run continuous watcher:

powershell
Copy code
python run/auto_cycle.py
14 — Troubleshooting (common fixes)
Docker issues
Ensure Docker Desktop is running.

Enable virtualization in BIOS (VT-x/AMD-V).

Restart your PC if containers fail to start.

Circular import (weaviate)
If you get:

pgsql
Copy code
ImportError: cannot import name '__version__'
Fix by reinstalling inside the venv:

powershell
Copy code
pip uninstall weaviate-client -y
pip install weaviate-client
CrewAI YAML errors
If you see:

pgsql
Copy code
AttributeError: 'str' object has no attribute 'get'
→ Your YAML files (agents.yaml, tasks.yaml) likely have formatting issues. Ensure each agent/task is specified as a mapping with fields (description, agent, expected_output), not as a bare string.

Missing fastapi
powershell
Copy code
pip install fastapi uvicorn
insert_sensor_event() argument error
Call it like:

python
Copy code
insert_sensor_event(timestamp=data["timestamp"], node_id=data["node_id"], methane_ppm=data["methane_ppm"], scenario=data.get("scenario", "normal"))
Crew doesn’t run automatically
Check that background_tasks.add_task(run_crew_async) is present in api_server.py.









