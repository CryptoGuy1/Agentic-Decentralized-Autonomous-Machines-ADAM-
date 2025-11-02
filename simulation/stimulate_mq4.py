# simulate_mq4.py
import time
import random
import argparse
from data_layer.weaviate_client import insert_sensor_event

def run_simulation(rate=1.0, nodes=3, scenario="normal"):
    """
    rate: events per second
    nodes: number of simulated nodes
    """
    while True:
        node_id = f"node_{random.randint(1, nodes)}"
        # baseline
        if random.random() < 0.02 or scenario == "spike":
            methane = random.uniform(450.0, 850.0)  # spike
        else:
            methane = random.uniform(3.0, 9.0)  # normal ppm
        trace = insert_sensor_event(node_id=node_id, methane_ppm=methane, scenario=scenario)
        print(f"Inserted {trace} {node_id} {methane:.2f} ppm")
        time.sleep(1.0 / rate)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rate", type=float, default=0.5)
    parser.add_argument("--nodes", type=int, default=4)
    parser.add_argument("--scenario", type=str, default="normal")
    args = parser.parse_args()
    run_simulation(rate=args.rate, nodes=args.nodes, scenario=args.scenario)
