

# 🧠 ADAM — Methane Monitoring System  
### *(CrewAI + Weaviate + Node-RED Integration)*

---

## 🚀 Overview

**ADAM** is an **autonomous methane monitoring and alert system** built with:

- 🤖 **CrewAI** — autonomous reasoning & workflow orchestration  
- 🧩 **Weaviate** — vector database for storing and querying readings  
- 🌐 **Node-RED** — data simulation & sensor integration  

It continuously collects methane readings, detects anomalies, and sends **email alerts** when concentrations exceed safety thresholds.

---

## 🧰 Features

✅ Real-time methane data ingestion  
✅ AI-driven validation & anomaly detection  
✅ Continuous background monitoring  
✅ Automated email notifications  
✅ Node-RED flow for real-world simulation  
✅ Vector database (Weaviate) integration  

---

## 💻 Requirements (for macOS & Windows)

| Tool | Purpose |
|------|----------|
| **macOS 13+** or **Windows 10/11** | OS compatibility |
| **Python 3.12+** | CrewAI & FastAPI runtime |
| **Docker Desktop** | Runs Weaviate database |
| **VS Code** *(recommended)* | Code editing |
| **Node.js + Node-RED** | Sensor data simulation |
| **Gmail App Password** *(optional)* | Email alerting |

---

- `methane_monitoring_ai/`
  - `autonomous/` — CREWAI / cognitive layer
    - `crew_box.py` — CrewAI orchestration (agents & tasks)
    - `reasoning_agent.py` — LLM reasoning and anomaly decision logic
    - `email_alert.py` — Gmail alert helper
    - `api_server.py` — FastAPI ingestion server (receives Node-RED or HTTP posts)
  - `data_layer/` — Vector DB schema and Weaviate utilities
    - `create_schema.py` — Create Weaviate `SensorEvent` class
    - `test_weaviate_connection.py` — Connection sanity checks
    - `weaviate_client.py` — Weaviate connection and CRUD helpers
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

## ⚙️ Installation — macOS (Terminal)

### 🪜 Step 1 — Clone the repository

git clone <your-repo-url>
cd adams
🪜 Step 2 — Create & activate virtual environment
bash
Copy code
python3 -m venv .venv
source .venv/bin/activate
You’ll see (.venv) at the start of your prompt.

🪜 Step 3 — Install dependencies
bash
Copy code
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
⚠️ If you see
ERROR: No matching distribution found for smtplib,
remove smtplib from requirements.txt (it’s built-in to Python).

🔐 Step 4 — Configure Environment Variables
Create a .env file in your project root:

ini
Copy code
WEAVIATE_URL=http://localhost:8080
ABSOLUTE_EMERGENCY_PPM=5000
GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password
💡 Use a Gmail App Password (not your normal password).
Go to Google Account → Security → App Passwords to create one.

🐋 Step 5 — Run Weaviate with Docker
Start Docker Desktop, then run:

bash
Copy code
docker compose up -d
docker compose logs -f
Wait until you see:

vbnet
Copy code
✅ Weaviate is ready to receive requests
Check readiness:

bash
Copy code
curl http://127.0.0.1:8080/v1/.well-known/ready
If you get a JSON response → ✅ Weaviate is running.

🧱 Step 6 — Create the Weaviate Schema
Run once:

bash
Copy code
python -m data_layer.create_schema
Expected output:

Copy code
✅ Collection created successfully
or

arduino
Copy code
Collection already exists
🌐 Step 7 — Start the FastAPI Ingestion Server
This server receives methane readings from Node-RED or manual tests.

bash
Copy code
python -m autonomous.api_server
You’ll see:

makefile
Copy code
INFO:     Application startup complete.
API runs at → http://127.0.0.1:8000

🧪 Step 8 — Send a Test Methane Reading
bash
Copy code
curl -X POST http://127.0.0.1:8000/sensor-data \
  -H "Content-Type: application/json" \
  -d '{"timestamp":"2025-10-23T14:00:00Z","node_id":"CH4_001","methane_ppm":5500.0}'
Expected response:

json
Copy code
{
  "status": "ok",
  "message": "Data stored, crew triggered"
}
🔍 Step 9 — Verify Data Storage
✅ Option 1 — via FastAPI
bash
Copy code
curl "http://127.0.0.1:8000/recent-readings?limit=5"
✅ Option 2 — via GraphQL (Weaviate)
bash
Copy code
curl -X POST http://127.0.0.1:8080/v1/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ Get { SensorEvent(limit:5) { node_id methane_ppm timestamp } } }"}'
🤖 Step 10 — Run the CrewAI Monitor
▶️ Manual Run
bash
Copy code
python -m autonomous.crew
🔁 Continuous Monitoring
bash
Copy code
python run/auto_cycle.py
Press Ctrl + C to stop the loop.

🔄 Step 11 — Simulate Data with Node-RED
⚙️ Install & Launch
bash
Copy code
npm install -g --unsafe-perm node-red
node-red
Open Node-RED → http://127.0.0.1:1880

🧩 Import Flow
Click Import → simulation/node_red_flow.json

Click Deploy

🟢 Controls
Button	Action
🟢 Resume Flow	Starts sending methane readings every 15 seconds
🛑 Stop Flow	Pauses data generation

Every few minutes, Node-RED injects a breach event (5000–6500 ppm)
to test anomaly detection and email alerts.

🧭 Common macOS Commands
Task	Command
Activate venv	source .venv/bin/activate
Start Weaviate	docker compose up -d
Create schema	python -m data_layer.create_schema
Start API	python -m autonomous.api_server
Send test data	curl -X POST http://127.0.0.1:8000/sensor-data ...
Run Crew manually	python -m autonomous.crew
Continuous monitor	python run/auto_cycle.py
Stop monitoring	Ctrl + C

🧩 Troubleshooting
Issue	Fix
🐋 Docker not starting	Open Docker Desktop manually
⚙️ CrewAI YAML error	Recheck indentation in agents.yaml / tasks.yaml
🚫 ModuleNotFoundError: fastapi	Run pip install fastapi uvicorn
📧 Email not sending	Verify .env Gmail credentials
🔁 Crew loop never stops	Press Ctrl + C
🧬 “No schema present” in Weaviate	Re-run python -m data_layer.create_schema

🧠 Next Steps
Connect real methane sensors (MQTT → FastAPI)

Deploy via Docker Compose end-to-end

Add a Grafana dashboard for live visualization

Extend CrewAI to manage multiple sensors

✅ Quick Start Summary
bash
Copy code
# 1. Activate venv
source .venv/bin/activate

# 2. Start database
docker compose up -d

# 3. Create schema
python -m data_layer.create_schema

# 4. Start API server
python -m autonomous.api_server

# 5. Open Node-RED and deploy the flow
🎉 You’re all set!
ADAM will autonomously monitor methane levels and trigger alerts when dangerous readings are detected.
Stay safe and smart with CrewAI + Weaviate + Node-RED 🚨

yaml
Copy code

---

Would you like me to add **badges** (e.g. Python 3.12 | Docker | FastAPI | CrewAI |









