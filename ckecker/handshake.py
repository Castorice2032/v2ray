# handshake
"""
ckecker/handshake_layer.py

Central handshake layer: runs connectivity tests against Xray configurations.
Supports JSON config file or dict, uses central logging, and returns boolean result.
"""
import subprocess
import time
import signal
import tempfile
import json
import os
from pathlib import Path
import requests
from logs.log import LoggerManager

# Optional schema validation toggle
ENABLE_SCHEMA_VALIDATION = False
XRAY_SCHEMA = None

if ENABLE_SCHEMA_VALIDATION:
    import jsonschema
    SCHEMA_PATH = Path(__file__).resolve().parent.parent / "config" / "xray.json"
    try:
        with open(SCHEMA_PATH, encoding="utf-8") as f:
            XRAY_SCHEMA = json.load(f)
    except Exception:
        XRAY_SCHEMA = None

class HandshakeLayer:
    """
    Central layer for performing handshake tests on Xray configurations.
    """
    _xray_bin = "xray"
    logger = LoggerManager.get_logger("ckecker.handshake_layer")

    @classmethod
    def set_xray_bin(cls, path: str):
        """Configure the path to the Xray binary."""
        cls._xray_bin = path
        cls.logger.debug(f"Xray binary set to: {path}")

    @classmethod
    def handshake(cls, config, timeout: int = 10) -> bool:
        """
        Perform handshake test. `config` can be a file path or a dict.
        Returns True on successful connectivity, False otherwise.
        """
        if isinstance(config, (str, Path)):
            cfg_path = str(config)
            try:
                cfg_dict = json.loads(Path(cfg_path).read_text())
            except Exception as e:
                cls.logger.error(f"Failed to load config from {cfg_path}: {e}")
                return False
        elif isinstance(config, dict):
            cfg_dict = config
            tf = tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json")
            json.dump(cfg_dict, tf)
            tf.flush()
            cfg_path = tf.name
            cls.logger.debug(f"Temporary config written to {cfg_path}")
        else:
            cls.logger.error("Invalid config type; must be file path or dict.")
            return False

        # Optional JSON schema validation
        if ENABLE_SCHEMA_VALIDATION and XRAY_SCHEMA is not None:
            try:
                jsonschema.validate(instance=cfg_dict, schema=XRAY_SCHEMA)
                cls.logger.debug("Config validated against Xray schema.")
            except Exception as e:
                cls.logger.error(f"Config validation failed: {e}")
                if isinstance(config, dict): os.remove(cfg_path)
                return False

        # Sanity check: find SOCKS inbound
        inbounds = cfg_dict.get("inbounds", [])
        inbound = next((i for i in inbounds if i.get("protocol") == "socks"), None)
        if not inbound:
            cls.logger.error("No 'socks' inbound entry found in config.")
            if isinstance(config, dict): os.remove(cfg_path)
            return False
        host = inbound.get("listen", "127.0.0.1")
        port = inbound.get("port")
        if not port:
            cls.logger.error("Inbound 'port' is missing.")
            if isinstance(config, dict): os.remove(cfg_path)
            return False

        # Launch Xray
        try:
            proc = subprocess.Popen(
                [cls._xray_bin, "run", "-config", cfg_path],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1
            )
            cls.logger.info(f"Launched Xray: {cls._xray_bin} run -config {cfg_path}")
        except Exception as e:
            cls.logger.error(f"Failed to launch Xray: {e}")
            if isinstance(config, dict): os.remove(cfg_path)
            return False

        # Wait for "started"
        started = False
        deadline = time.time() + timeout
        while time.time() < deadline:
            line = proc.stdout.readline()
            if not line:
                continue
            cls.logger.debug(f"Xray output: {line.strip()}")
            lower = line.lower()
            if "started" in lower:
                started = True
                cls.logger.info("Xray started successfully.")
                break
            if "failed" in lower:
                cls.logger.error("Xray reported failure during startup.")
                proc.kill()
                if isinstance(config, dict): os.remove(cfg_path)
                return False

        if not started:
            cls.logger.error("Xray did not start within timeout.")
            proc.kill()
            if isinstance(config, dict): os.remove(cfg_path)
            return False

        # Send test request through SOCKS
        proxies = {
            "http": f"socks5h://{host}:{port}",
            "https": f"socks5h://{host}:{port}"
        }
        ok = False
        try:
            resp = requests.get("https://www.gstatic.com/generate_204", proxies=proxies, timeout=8)
            ok = resp.status_code in (200, 204)
            if ok:
                cls.logger.info("Handshake HTTP request succeeded.")
            else:
                cls.logger.warning(f"Handshake HTTP returned status {resp.status_code}.")
        except Exception as e:
            cls.logger.error(f"Handshake HTTP request error: {e}")
        finally:
            proc.send_signal(signal.SIGINT)
            proc.wait(timeout=5)
            cls.logger.debug("Xray process terminated.")
            if isinstance(config, dict): os.remove(cfg_path)

        return ok
