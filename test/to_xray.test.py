#!/usr/bin/env python3
"""
Test runner for converters/to_xray: loads sample nodes, converts to Xray config, and saves output.
"""
import sys
import json
from pathlib import Path

# ensure project root in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import converters
from converters import load_nodes, convert_nodes

if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    # Path to sample nodes JSON
    nodes_file = root / "data" /  "config.json"
    # Path to base Xray config schema
    base_cfg_file = root / "config" / "xray.json"
    # Output path for generated Xray config
    out_file = root / "data" / "xray.test.json"

    # Load nodes
    try:
        nodes = load_nodes(nodes_file)
    except Exception as e:
        print(f"❌ Failed to load nodes: {e}")
        sys.exit(1)

    # Convert nodes
    outbounds = convert_nodes(nodes)

    # Load base Xray config (strip comments)
    try:
        raw = base_cfg_file.read_text()
        import re
        # remove /* ... */ comments
        raw = re.sub(r'/\*.*?\*/', '', raw, flags=re.DOTALL)
        # remove // comments
        raw = re.sub(r'//.*$', '', raw, flags=re.MULTILINE)
        base_cfg = json.loads(raw)
    except Exception:
        print("⚠️ Could not parse base Xray config; using default base config")
        base_cfg = {
            "log": {"loglevel": "warning"},
            "inbounds": [
                {"tag": "socks", "listen": "127.0.0.1", "port": 1080, "protocol": "socks", "settings": {"auth": "noauth"}}
            ],
            "outbounds": []
        }

    # Merge and save
    base_cfg["outbounds"] = outbounds
    out_file.write_text(json.dumps(base_cfg, indent=2))
    print(f"✅ Xray test config generated: {out_file}")
    sys.exit(0)
