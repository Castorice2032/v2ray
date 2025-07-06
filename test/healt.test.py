# Simple test for health_checker.ping_host
# Standard libs
import sys, os, json
from pathlib import Path
import logging

# allow importing ckecker package from project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ckecker.health import health_check_nodes
from ckecker.health_checker import set_use_nmap

# Suppress verbose health_checker logs for cleaner output
logging.getLogger('health_checker').setLevel(logging.WARNING)

# Decide whether to use nmap for health checks
USE_NMAP = True  # set to False to disable nmap scanning
set_use_nmap(USE_NMAP)

HYSTERIA2_FILE = Path(__file__).resolve().parent.parent / "data" / "json" / "hysteria2.json"

if __name__ == "__main__":
    # Load real hysteria2 nodes from JSON
    try:
        nodes = json.load(open(HYSTERIA2_FILE, encoding="utf-8"))
        print(f"Loaded {len(nodes)} nodes from {HYSTERIA2_FILE}")
    except Exception as e:
        print(f"Failed to load hysteria2 JSON: {e}")
        sys.exit(1)
    # Perform health checks
    results = health_check_nodes(nodes)
    # Print results with tags
    for item, res in zip(nodes, results):
        tag = item.get("tag") or item.get("config", {}).get("server")
        print(f"{tag} -> {res}")
