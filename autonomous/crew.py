# autonomous/crew.py
import os
import yaml
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
from data_layer.weaviate_client import ensure_schema
from .reasoning_agent import call_chatgpt_reasoner
import logging


DEFAULT_THRESHOLD = float(os.getenv("METHANE_THRESHOLD_PPM", "10.0"))

# --- Robust Config Path Handling ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIRS = [
    os.path.join(BASE_DIR, "config"),                  # autonomous/config
    os.path.join(os.path.dirname(BASE_DIR), "config")  # root/config fallback
]

CONFIG_DIR = None
for d in CONFIG_DIRS:
    if os.path.exists(d):
        CONFIG_DIR = d
        break

if CONFIG_DIR is None:
    logging.warning("⚠️ No config directory found.")
else:
    print(f"🔍 Using config directory: {CONFIG_DIR}")

def load_yaml_config(filename):
    """Load a YAML file safely, returning {} if missing or invalid."""
    if CONFIG_DIR is None:
        logging.warning(f"⚠️ No config directory set; cannot load {filename}")
        return {}
    path = os.path.join(CONFIG_DIR, filename)
    if not os.path.exists(path):
        logging.warning(f"⚠️ File not found: {path}")
        return {}
    with open(path, "r") as f:
        try:
            data = yaml.safe_load(f)
            print(f"✅ Loaded {filename} successfully.")
            return data or {}
        except yaml.YAMLError as e:
            logging.error(f"YAML error in {filename}: {e}")
            return {}

AGENTS_CONFIG = load_yaml_config("agents.yaml")
TASKS_CONFIG = load_yaml_config("tasks.yaml")

@CrewBase
class MethaneMonitoringCrew:
    """Main CrewAI orchestration class for methane monitoring"""

    agents: List[BaseAgent]
    tasks: List[Task]

    # === Define agents ===
    @agent
    def sensor_agent(self) -> Agent:
        return Agent(config=AGENTS_CONFIG["sensor_agent"], verbose=True)

    @agent
    def validator_agent(self) -> Agent:
        return Agent(config=AGENTS_CONFIG["validator_agent"], verbose=True)

    @agent
    def decision_agent(self) -> Agent:
        return Agent(config=AGENTS_CONFIG["decision_agent"], verbose=True)

    @agent
    def coordinator_agent(self) -> Agent:
        return Agent(config=AGENTS_CONFIG["coordinator_agent"], verbose=True)

    @task
    def collect_data_task(self) -> Task:
        task_conf = TASKS_CONFIG["collect_data_task"]
        return Task(
            description=task_conf["description"],
            agent=self.sensor_agent(),
            expected_output=task_conf["expected_output"]
        )

    @task
    def validate_data_task(self) -> Task:
        task_conf = TASKS_CONFIG["validate_data_task"]
        return Task(
            description=task_conf["description"],
            agent=self.validator_agent(),
            expected_output=task_conf["expected_output"]
        )

    @task
    def analyze_task(self) -> Task:
        task_conf = TASKS_CONFIG["analyze_task"]
        return Task(
            description=task_conf["description"],
            agent=self.decision_agent(),
            expected_output=task_conf["expected_output"]
        )

    @task
    def report_task(self) -> Task:
        task_conf = TASKS_CONFIG["report_task"]
        return Task(
            description=task_conf["description"],
            agent=self.coordinator_agent(),
            expected_output=task_conf["expected_output"],
            output_file="methane_alert_report.md"
        )

    # === Define Crew ===
    @crew
    def crew(self) -> Crew:
        # Ensure Weaviate schema exists before running
        ensure_schema()
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )


def handle_detection_and_notify(anomalies: list[dict], report_text: str):
    """
    Called after detection/LLM reasoning. `anomalies` is a list of dicts of flagged events.
    `report_text` is the text output already prepared (report from agent).
    """
    if not anomalies:
        return False

    subject = f"⚠️ Methane Alert — {len(anomalies)} anomaly(ies) detected"
    body = f"Anomalies found:\n\n{report_text}\n\n---\nAutomated message from Methane Monitoring."
    # recipients default to ALERT_TO in .env if to_addrs None
    try:
        send_email_alert(subject, body, None)
        print("✅ Alert email sent.")
        return True
    except Exception as e:
        print("❌ Failed to send alert email:", e)
        return False


if __name__ == "__main__":
    print("🚀 Launching Methane Monitoring Crew...")
    crew_instance = MethaneMonitoringCrew()
    crew_instance.crew().kickoff()


