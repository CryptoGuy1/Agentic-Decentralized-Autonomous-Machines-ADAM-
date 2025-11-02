# autonomous/crew.py
import os
import yaml
import logging
from typing import List, Dict, Any, Tuple

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent

# Weaviate helpers
from data_layer.weaviate_client import ensure_schema, get_recent_readings

# Reasoner (your LLM wrapper) - expected to accept a list[dict] and return textual reasoning
from .reasoning_agent import call_chatgpt_reasoner

# Email alert function - make sure this file exists at autonomous/email_alert.py
from .email_alert import send_email_alert

# Threshold from env
DEFAULT_THRESHOLD = float(os.getenv("METHANE_THRESHOLD_PPM", "80.0"))

# --- Config loader (robust) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIRS = [
    os.path.join(BASE_DIR, "config"),                  # autonomous/config
    os.path.join(os.path.dirname(BASE_DIR), "config")  # repo-root/config fallback
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


def load_yaml_config(filename: str) -> Dict[str, Any]:
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
        return Agent(config=AGENTS_CONFIG.get("sensor_agent", {}), verbose=True)

    @agent
    def validator_agent(self) -> Agent:
        return Agent(config=AGENTS_CONFIG.get("validator_agent", {}), verbose=True)

    @agent
    def decision_agent(self) -> Agent:
        return Agent(config=AGENTS_CONFIG.get("decision_agent", {}), verbose=True)

    @agent
    def coordinator_agent(self) -> Agent:
        return Agent(config=AGENTS_CONFIG.get("coordinator_agent", {}), verbose=True)

    # === Tasks as explicit Task objects (avoid YAML parsing pitfalls) ===
    @task
    def collect_data_task(self) -> Task:
        tc = TASKS_CONFIG.get("collect_data_task", {})
        return Task(description=tc.get("description", "Collect data"), agent=self.sensor_agent(),
                    expected_output=tc.get("expected_output", ""))

    @task
    def validate_data_task(self) -> Task:
        tc = TASKS_CONFIG.get("validate_data_task", {})
        return Task(description=tc.get("description", "Validate data"), agent=self.validator_agent(),
                    expected_output=tc.get("expected_output", ""))

    @task
    def analyze_task(self) -> Task:
        tc = TASKS_CONFIG.get("analyze_task", {})
        return Task(description=tc.get("description", "Analyze data"), agent=self.decision_agent(),
                    expected_output=tc.get("expected_output", ""))

    @task
    def report_task(self) -> Task:
        tc = TASKS_CONFIG.get("report_task", {})
        return Task(description=tc.get("description", "Report"), agent=self.coordinator_agent(),
                    expected_output=tc.get("expected_output", ""), output_file="methane_alert_report.md")

    # === Define Crew ===
    @crew
    def crew(self) -> Crew:
        ensure_schema()
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )


if __name__ == "__main__":
    print("🚀 Launching Methane Monitoring Crew (local run)")
    crew_instance = MethaneMonitoringCrew()
    _ = crew_instance.crew().kickoff()  # run Crew tasks (agents) once
    print("✅ Crew completed. Running detection & notification pass...")
    ok, report = run_detection_and_notify()
    print("Notification sent?:", ok)
    print("Report summary (first 400 chars):\n", report[:400])
