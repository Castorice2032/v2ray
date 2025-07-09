#!/usr/bin/env python3
"""
Test run_handshake_config from ckecker/handshake.py against each outbound
in the converted Xray config at data/xray.test.json.
Prints each server tag and boolean result.
"""
import sys
import json
import tempfile
from pathlib import Path

# ensure project root is first in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ckecker.handshake import HandshakeLayer

if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    # configure Xray binary
    HandshakeLayer.set_xray_bin(str(root / "server" / "xray"))
    # load converted Xray config
    cfg_file = root / "data" / "xray.generated.json"
    try:
        xcfg = json.loads(cfg_file.read_text())
    except Exception as e:
        print(f"❌ Failed to load converted config: {e}")
        sys.exit(1)

    outbounds = xcfg.get("outbounds", [])
    if not outbounds:
        print("❌ No outbounds to test in converted config.")
        sys.exit(1)

    any_fail = False
    for ob in outbounds:
        tag = ob.get("tag") or ob.get("protocol")
        # build minimal Xray config dict
        test_cfg = {
            "log": {"loglevel": "warning"},
            "dns": {},
            "inbounds": [{"tag": "socks", "listen": "127.0.0.1", "port": 1080, "protocol": "socks", "settings": {"auth": "noauth"}}],
            "outbounds": [ob],
            "routing": {"rules": [{"type": "field", "outboundTag": tag, "network": "tcp"}]}
        }
        # write to temp file
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as tf:
            json.dump(test_cfg, tf)
            tf.flush()
            path = tf.name
        # run handshake using HandshakeLayer
        result = HandshakeLayer.handshake(path, timeout=10)
        # clean up
        try:
            Path(path).unlink()
        except Exception:
            pass
        print(f"{tag}: {result}")
        if not result:
            any_fail = True

    sys.exit(1 if any_fail else 0)
