# Veri-ADAM — Methane Monitoring AI (CrewAI + Weaviate + Node-RED)

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
- **Windows 10 or 11**  
- **Python 3.12.x** (your current version works fine)  
- **Docker Desktop** (for Weaviate database)  
- **VS Code** (recommended editor)  
- **Node-RED** (for sensor data simulation)  
- **Gmail App Password** (for alert emails — optional)

---

## 3 — Project layout

methane_monitoring_ai/
├── autonomous/
│ ├── crew.py # CrewAI orchestration (agents & tasks)
│ ├── reasoning_agent.py # Reasoning logic for anomalies
│ ├── weaviate_client.py # CRUD operations for Weaviate
│ ├── email_alert.py # Sends email alerts (optional)
│ └── api_server.py # FastAPI ingestion server
│
├── data_layer/
│ ├── create_schema.py # Defines SensorEvent schema in Weaviate
│ ├── test_weaviate_connection.py
│ └── weaviate_utils.py
│
├── simulation/
│ ├── simulate_mq4.py
│ ├── node_publisher.py
│ └── node_red_flow.json # Ready-to-import Node-RED flow
│
├── config/
│ ├── agents.yaml
│ ├── tasks.yaml
│ └── settings.yaml
│
├── run/
│ ├── auto_cycle.py # Automatic loop for crew triggering
│ ├── main.py
│ └── test_anomaly_cycle.py
│
├── docker-compose.yml
├── requirements.txt
├── README.md
└── .env

yaml
Copy code

---

## 4 — Step-by-step installation (Windows PowerShell)

> 🔹 Open PowerShell normally for setup commands  
> 🔹 Use Administrator PowerShell only for Docker install or virtualization setup

### Step 1 — Clone or download the project
```powershell
git clone <your-github-repo-url>
cd methane_monitoring_ai
Step 2 — Create and activate a virtual environment
powershell
Copy code
python -m venv .venv
& ".\.venv\Scripts\Activate.ps1"
You’ll see (.venv) at the start of your prompt.

Step 3 — Install dependencies
powershell
Copy code
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
⚠️ If you see:

yaml
Copy code
ERROR: No matching distribution found for smtplib
Remove smtplib from requirements.txt (it’s built into Python).

5 — Configure .env file
Create a .env file at your project root with the following:

ini
Copy code
WEAVIATE_URL=http://localhost:8080
METHANE_THRESHOLD_PPM=80
GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password_here
Use a Gmail App Password, not your regular password.
Generate one under: Google Account → Security → App Passwords.

6 — Run Weaviate (Docker)
Weaviate is your vector database for storing methane readings.

Step 1 — Start Docker Desktop
Ensure virtualization (Intel VT-x or AMD-V) is enabled in your BIOS.

Step 2 — Launch Weaviate
powershell
Copy code
docker compose up -d
docker compose logs -f
Wait until you see:
✅ Weaviate is ready to receive requests

Check it manually:

powershell
Copy code
Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/.well-known/ready"
If you get a JSON response → it's working.

7 — Create Weaviate schema
Run this command once:

powershell
Copy code
python -m data_layer.create_schema
If you see:

Copy code
✅ Weaviate v4 collection created successfully.
or

arduino
Copy code
Collection already exists.
—you’re good.

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
API runs on:
➡️ http://127.0.0.1:8000

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
This runs:

Collect sensor data

Validate readings

Detect anomalies

Generate report

Automatic run (recommended)
The crew is already triggered automatically in api_server.py whenever new data arrives via /sensor-data.

Alternatively, you can run a loop watcher:

powershell
Copy code
python run/auto_cycle.py
This watches Weaviate for new data and triggers CrewAI periodically.

12 — Node-RED simulation
If you want to simulate live sensors:

Open Node-RED in your browser (http://127.0.0.1:1880).

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
14 — Troubleshooting
🧩 Docker issues
Ensure Docker Desktop is running.

Enable virtualization in BIOS (VT-x/AMD-V).

Restart your PC if containers fail to start.

🧩 Circular import (weaviate)
If you get:

pgsql
Copy code
ImportError: cannot import name '__version__'
→ Uninstall the global weaviate and reinstall inside your venv:

powershell
Copy code
pip uninstall weaviate-client -y
pip install weaviate-client
🧩 CrewAI YAML errors
pgsql
Copy code
AttributeError: 'str' object has no attribute 'get'
→ Your YAML files (agents.yaml, tasks.yaml) have formatting issues.
Each key should have nested fields (description, agent, etc.), not plain strings.

🧩 Missing fastapi
powershell
Copy code
pip install fastapi uvicorn
🧩 insert_sensor_event() argument error
Make sure you call:

python
Copy code
insert_sensor_event(timestamp=data["timestamp"], node_id=data["node_id"], methane_ppm=data["methane_ppm"], scenario=data.get("scenario", "normal"))
🧩 Crew doesn’t run automatically
Check if background_tasks.add_task(run_crew_async) exists in your api_server.py.

15 — Next steps & notes
✅ Add proper logging and alerts.
✅ Deploy Weaviate in the cloud for long-term use.
✅ Containerize the entire stack with Docker Compose (Weaviate + FastAPI).
✅ Optional: Integrate blockchain or decentralized logging later for sensor authenticity.