#!/usr/bin/env python
import sys
import warnings
from datetime import datetime
from autonomous.crew import MethaneMonitoringCrew

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# ====================================================
# ADAM Methane Monitoring System
# ====================================================
# This main file allows you to run, train, or test your CrewAI agents
# locally or during simulation (e.g., from Node-RED).
# Each function below triggers a different execution mode.
# ====================================================

def run():
    """
    Run the methane monitoring crew simulation.
    Example: Collect -> Validate -> Analyze -> Report
    """
    inputs = {
        'sensor_id': 'node_04',
        'location': 'WABI_Field',
        'timestamp': str(datetime.now()),
        'methane_ppm': 12.5,  # simulated reading
        'threshold_ppm': 10.0
    }

    try:
        MethaneMonitoringCrew().crew().kickoff(inputs=inputs)
    except Exception as e:
        raise Exception(f"❌ Error during methane monitoring crew run: {e}")


def train():
    """
    Train the crew (for simulation learning or reasoning fine-tuning).
    Usage: python main.py train 5 crew_memory.json
    """
    inputs = {
        'sensor_did': 'node_training',
        'location': 'simulation_lab',
        'current_year': str(datetime.now().year)
    }

    try:
        MethaneMonitoringCrew().crew().train(
            n_iterations=int(sys.argv[1]),
            filename=sys.argv[2],
            inputs=inputs
        )
    except Exception as e:
        raise Exception(f"❌ Error while training the methane monitoring crew: {e}")


def replay():
    """
    Replay a specific methane monitoring task (for debugging or audit).
    Usage: python main.py replay <task_id>
    """
    try:
        MethaneMonitoringCrew().crew().replay(task_id=sys.argv[1])
    except Exception as e:
        raise Exception(f"❌ Error while replaying the methane monitoring crew: {e}")


def test():
    """
    Test the methane monitoring crew (for model evaluation).
    Usage: python main.py test 3 gpt-4
    """
    inputs = {
        'sensor_did': 'node_test',
        'location': 'test_field',
        'methane_ppm': 8.7,
        'threshold_ppm': 10.0,
        'timestamp': str(datetime.now())
    }

    try:
        MethaneMonitoringCrew().crew().test(
            n_iterations=int(sys.argv[1]),
            eval_llm=sys.argv[2],
            inputs=inputs
        )
    except Exception as e:
        raise Exception(f"❌ Error while testing the methane monitoring crew: {e}")


if __name__ == "__main__":
    # Default behavior if run without arguments
    run()
