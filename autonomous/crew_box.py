# autonomous/crew.py
import os
import yaml
import json
import logging
import time
import signal
from datetime import datetime, timezone
from data_layer.weaviate_client import close_client

from typing import List, Dict, Any, Tuple
from statistics import mean, stdev

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent

# ✅ Import your fixed Weaviate helpers
from data_layer.weaviate_client import ensure_schema, get_recent_readings

# ✅ Reasoner and Email modules
from .reasoning_agent import call_chatgpt_reasoner
from .email_alert import send_email_alert


# -------------------------
# CONFIG LOADING
# -------------------------
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


# -------------------------
# CREWAI CONFIGURATION
# -------------------------
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

    # === Define tasks ===
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
        return Crew(agents=self.agents, tasks=self.tasks, process=Process.sequential, verbose=True)


# -------------------------
# DETECTION & ALERT LOGIC
# -------------------------
ABSOLUTE_EMERGENCY_PPM = float(os.getenv("ABSOLUTE_EMERGENCY_PPM", "5000.0"))

def _safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default


def detect_anomalies_from_readings(
    readings: list[dict],
    absolute_threshold: float = ABSOLUTE_EMERGENCY_PPM,
) -> list[dict]:
    """
    Detect anomalies based only on an absolute methane threshold.
    Anything above absolute_threshold is considered an alert.
    """
    anomalies = []
    for r in readings:
        ppm = _safe_float(r.get("methane_ppm"))
        if ppm >= absolute_threshold:
            anomalies.append({
                "reason": f"ppm >= {absolute_threshold}",
                "reading": r
            })
    return anomalies


# -------------------------
# RUN LOOP (continuous monitoring)
# -------------------------

# Configurable via environment
CHECK_INTERVAL_SECONDS = float(os.getenv("CHECK_INTERVAL_SECONDS", "15"))     # poll interval
ALERT_COOLDOWN_SECONDS = float(os.getenv("ALERT_COOLDOWN_SECONDS", "300"))  # don't re-alert the same trace for this many seconds

# track alerts to avoid duplicates: map trace_id -> last_alert_unix_ts
_last_alert_ts: dict[str, float] = {}

def _should_alert_for_trace(trace_id: str) -> bool:
    """Return True if we should alert for this trace_id (not alerted recently)."""
    if not trace_id:
        return True
    now = time.time()
    last = _last_alert_ts.get(trace_id)
    if last is None:
        return True
    return (now - last) >= ALERT_COOLDOWN_SECONDS

def _mark_alert_sent(trace_id: str) -> None:
    if not trace_id:
        return
    _last_alert_ts[trace_id] = time.time()

def run_detection_once_and_maybe_notify(limit: int = 50, send_to: list | None = None) -> Tuple[bool, str]:
    """
    Run one detection pass, but only send email for new anomalies (deduplicated).
    Returns (sent_flag, report_text).
    """
    readings = get_recent_readings(limit=limit) or []
    if not readings:
        return False, "No readings found."

    anomalies = detect_anomalies_from_readings(readings)
    if not anomalies:
        return False, "No anomalies found."

    # filter anomalies to ones that should actually trigger an alert now
    new_anomalies = []
    for a in anomalies:
        r = a.get("reading", {}) if isinstance(a, dict) else a
        trace_id = r.get("trace_id") or r.get("traceid") or r.get("id") or ""
        if _should_alert_for_trace(trace_id):
            new_anomalies.append((trace_id, r))

    if not new_anomalies:
        return False, "Anomalies present but none are new (cooldown)."

    # build minimal anomalies list for reasoner (readings only)
    anomalies_readings = [r for (_tid, r) in new_anomalies]

    # call reasoner
    try:
        context = {"anomalies": anomalies_readings, "recent_readings": readings}
        report = call_chatgpt_reasoner(anomalies_readings, context_readings=readings)
        report_text = json.dumps(report, indent=2, default=str) if not isinstance(report, str) else report
    except TypeError:
        # fallback if reasoner signature expects a single context dict
        try:
            report = call_chatgpt_reasoner({"anomalies": anomalies_readings, "context": readings})
            report_text = json.dumps(report, indent=2, default=str)
        except Exception as e:
            report_text = f"LLM reasoner failed: {e}"
    except Exception as e:
        report_text = f"LLM reasoner failed: {e}"

    # Determine recipients
    if send_to is None:
        raw = os.getenv("ALERT_TO") or os.getenv("GMAIL_USER")
        send_to = [raw] if raw else []

    if not send_to:
        return False, report_text + "\n\nNo recipients configured."

    # Compose email (unique subject to indicate number of new anomalies)
    subject = f"⚠️ Methane Alert: {len(new_anomalies)} new reading(s) ≥ {ABSOLUTE_EMERGENCY_PPM} ppm"
    body = f"Anomalies detected (threshold {ABSOLUTE_EMERGENCY_PPM} ppm):\n\n{report_text}\n\nRaw anomalies:\n{json.dumps([r for (_tid, r) in new_anomalies], indent=2, default=str)}"

    # Attempt to send
    try:
        send_email_alert(subject, body, send_to)
    except Exception as e:
        return False, f"{report_text}\n\nEmail error: {e}"

    # mark each trace as alerted now
    for (tid, _r) in new_anomalies:
        _mark_alert_sent(tid or f"anon-{int(time.time()*1000)}")

    return True, report_text


def _run_loop_forever(limit: int = 50, send_to: list | None = None):
    """
    Continuously poll, detect, and notify until interrupted by user (Ctrl+C).
    """
    print(f"▶️ Starting continuous monitor (interval {CHECK_INTERVAL_SECONDS}s). Ctrl+C to stop.")
    try:
        while True:
            try:
                sent, report = run_detection_once_and_maybe_notify(limit=limit, send_to=send_to)
                now = datetime.now(timezone.utc).isoformat()
                print(f"[{now}] Detection pass complete. Alert sent: {sent}. Summary: {str(report)[:200]}")
            except Exception as e:
                # log and continue (so transient errors don't crash loop)
                print("Error during detection pass:", e)
            time.sleep(CHECK_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("⏹️ Received KeyboardInterrupt — stopping monitoring loop.")
    finally:
        # ensure resources are closed
        try:
            close_client()
        except Exception:
            pass
        print("✅ Clean shutdown complete.")


# If run directly, start the crew once then run continuous monitoring loop
if __name__ == "__main__":
    print("🚀 Launching Methane Monitoring Crew (local run)")
    crew_instance = MethaneMonitoringCrew()
    _ = crew_instance.crew().kickoff()
    print("✅ Crew startup tasks completed. Entering continuous detection loop...")

    # Build explicit recipients list from env if present
    raw = os.getenv("ALERT_TO") or os.getenv("GMAIL_USER")
    recipients = [raw] if raw else None

    # Start continuous loop (runs until you press Ctrl+C)
    _run_loop_forever(limit=int(os.getenv("DETECTION_LIMIT", "50")), send_to=recipients)
