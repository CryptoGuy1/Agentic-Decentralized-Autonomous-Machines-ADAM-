
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



🧠 ADAM — Methane Monitoring System (CrewAI + Weaviate + Node-RED)
Purpose

ADAM is an autonomous methane monitoring and alert system that:

Collects methane readings (from Node-RED or API)

Stores them in Weaviate

Uses CrewAI to validate, analyze, and detect anomalies

Sends email alerts when methane exceeds safe limits

This guide helps you set up everything on macOS (MacBook, Intel or Apple Silicon).

🧩 Table of contents

Quick overview

Requirements

Project structure

Step-by-step setup (macOS Terminal)

Configure environment variables (.env)

Run Weaviate (Docker)

Create schema

Start the ingestion API

Test sending data

Check stored data

Run the CrewAI monitor

Simulate data with Node-RED

Useful macOS commands

Troubleshooting

Next steps

⚡ 1 — Quick overview

ADAM is composed of three layers:

Data layer (Weaviate) — stores methane readings

Autonomous layer (CrewAI) — validates and detects anomalies

Simulation layer (Node-RED) — generates test readings

When methane > 5000 ppm → a reasoning LLM summarizes the event and emails an alert.

💻 2 — Requirements (install these first)

You’ll need:

Tool	Description
macOS 13 or newer	Works on Intel and M-series chips
Python 3.12+	Install via python.org
 or Homebrew
Docker Desktop	For running Weaviate
Visual Studio Code	Recommended editor
Node-RED	For sensor data simulation
Gmail App Password (optional)	Used for alert emails

Install Homebrew if you don’t have it:

/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"


Then:

brew install python node
npm install -g --unsafe-perm node-red

🗂️ 3 — Project structure
methane_monitoring_ai/
├── autonomous/
│   ├── crew.py               # CrewAI orchestration
│   ├── reasoning_agent.py    # GPT reasoning logic
│   ├── email_alert.py        # Gmail alert handler
│   └── api_server.py         # FastAPI ingestion API
├── data_layer/
│   ├── weaviate_client.py
│   ├── create_schema.py
│   └── weaviate_utils.py
├── simulation/
│   ├── node_red_flow.json
│   └── simulate_mq4.py
├── config/
│   ├── agents.yaml
│   └── tasks.yaml
├── docker-compose.yml
├── requirements.txt
├── run/
│   ├── auto_cycle.py
│   └── test_anomaly_cycle.py
└── .env

🧰 4 — Step-by-step setup (macOS Terminal)

Open Terminal and follow along:

Step 1 — Clone the repository
git clone <your-repo-url>
cd adams

Step 2 — Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate


(You’ll see “(.venv)” at the start of your prompt)

Step 3 — Install dependencies
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt


If you see:

ERROR: No matching distribution found for smtplib


→ remove smtplib from requirements.txt (it’s built into Python).

🔐 5 — Configure .env

Create a file named .env in your project root:

WEAVIATE_URL=http://localhost:8080
ABSOLUTE_EMERGENCY_PPM=5000
GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password


⚠️ Use a Gmail App Password, not your normal password
Generate it here → Google Account → Security → App Passwords

🐋 6 — Run Weaviate (Docker)

Start Docker Desktop, then in Terminal:

docker compose up -d
docker compose logs -f


Wait until you see “Weaviate is ready”.

Check readiness:

curl http://127.0.0.1:8080/v1/.well-known/ready


If you get JSON output → ✅ working.

🧱 7 — Create the schema

Run once to create the Weaviate SensorEvent class:

python -m data_layer.create_schema


You should see:

✅ Weaviate collection created successfully.


or

Collection already exists.

🚀 8 — Start the ingestion API
python -m autonomous.api_server


Output should show:

INFO:     Application startup complete.


The API runs at → http://127.0.0.1:8000

🧪 9 — Send a test reading
curl -X POST http://127.0.0.1:8000/sensor-data \
  -H "Content-Type: application/json" \
  -d '{"timestamp":"2025-10-23T14:00:00Z","node_id":"CH4_001","methane_ppm":5500.0}'


Expected JSON response:

{
  "status": "ok",
  "message": "Data stored, crew triggered"
}

🔍 10 — Verify data in Weaviate

Via REST:

curl "http://127.0.0.1:8000/recent-readings?limit=5"


Via GraphQL:

curl -X POST http://127.0.0.1:8080/v1/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ Get { SensorEvent(limit:5) { node_id methane_ppm timestamp } } }"}'

🤖 11 — Run the CrewAI monitor
Manual run:
python -m autonomous.crew

Continuous run (auto-poll mode):
python run/auto_cycle.py


Press Ctrl + C to stop.

🌐 12 — Simulate data with Node-RED

Start Node-RED:

node-red


Visit http://127.0.0.1:1880

Import → simulation/node_red_flow.json

Click Deploy

Use the green and red inject buttons:

🟢 Resume Flow → start generating data every 15 s

🛑 Stop Flow → pause simulation

Every 5 minutes a synthetic anomaly (5000 – 6500 ppm) is injected.

🧭 13 — Useful macOS commands
Purpose	Command
Activate venv	source .venv/bin/activate
Start Weaviate	docker compose up -d
Create schema	python -m data_layer.create_schema
Start API	python -m autonomous.api_server
Send test data	curl -X POST http://127.0.0.1:8000/sensor-data ...
Run Crew manually	python -m autonomous.crew
Continuous watcher	python run/auto_cycle.py
Stop loop	Ctrl + C
🩺 14 — Troubleshooting
Issue	Fix
Docker not starting	Ensure Docker Desktop is running and virtualization is enabled
YAML format error	Recheck agents.yaml and tasks.yaml for correct indentation
No module named fastapi	pip install fastapi uvicorn
Email not sending	Verify .env Gmail credentials and that less-secure access is not required
Crew loop never ends	Press Ctrl + C to safely stop the continuous process
🧠 15 — Next steps

Connect real methane sensors through MQTT → FastAPI endpoint

Add multiple node IDs for distributed monitoring

Use Weaviate’s hybrid search to analyze spatial methane trends

Deploy FastAPI and CrewAI as Docker services

✅ You’re all set!
Run everything with:

source .venv/bin/activate
docker compose up -d
python -m data_layer.create_schema
python -m autonomous.api_server


Then open Node-RED to start your methane simulation and watch the CrewAI autonomously detect and email you any anomalies 🚨.









