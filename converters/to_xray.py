"""converters/to_xray.py

Convert a JSON list of proxy‑nodes (custom schema) to a **single** Xray‑compatible
configuration file.

▶︎ Supported protocols: shadowsocks, vmess, vless, trojan, hysteria (v1),
  hysteria2, tuic.
▶︎ Thread‑pool conversion for speed.
▶︎ Automatically merges with a base Xray config (if provided) instead of
  overwriting outbounds.
▶︎ Validates input nodes against `config/schema.json` (optional).
"""
from __future__ import annotations

import json, sys, argparse
from pathlib import Path
from typing import Dict, Callable, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from jsonschema import ValidationError

# Central logger
logger = logging.getLogger("ckecker.converter")

try:
    from jsonschema import validate  # optional – skip if not installed
except ImportError:  # pragma: no cover
    validate = None  # type: ignore

# ───────────────────────── paths ──────────────────────────────
BASE = Path(__file__).resolve().parent.parent
NODE_SCHEMA = BASE / "config" / "schema.json"
XRAY_SCHEMA = BASE / "config" / "xray.json"  # (not used here, but handy)

# ───────────────────── registry helper ───────────────────────
_converters: Dict[str, Callable[[Dict], Dict]] = {}

def register(protocol: str):
    """Decorator to register a converter for each protocol."""
    def deco(fn: Callable[[Dict], Dict]):
        _converters[protocol] = fn
        return fn
    return deco

# ────────────────────── util helpers ─────────────────────────

def _add_stream(node: Dict, outbound: Dict) -> None:
    """Propagate optional TLS / transport settings into outbound."""
    cfg = node.get("config", {})
    if tls := cfg.get("tls"):
        sec = "tls" if tls.get("enabled") else "none"
        outbound.setdefault("streamSettings", {})["security"] = sec
        if sec == "tls":
            outbound["streamSettings"]["tlsSettings"] = {
                k: v for k, v in tls.items() if k != "enabled"
            }
    if transport := cfg.get("transport"):
        outbound.setdefault("streamSettings", {}).update(
            {
                "network": transport.get("type", "tcp"),
                f"{transport.get('type', 'tcp')}Settings": {
                    k: v for k, v in transport.items() if k not in ("type",)
                },
            }
        )

# ───────────────────── protocol converters ───────────────────
@register("ss")
@register("shadowsocks")
def convert_ss(node: Dict) -> Dict:
    c = node["config"]
    ob = {
        "tag": node["tag"],
        "protocol": "shadowsocks",
        "settings": {
            "servers": [
                {
                    "address": c["server"],
                    "port": c["port"],
                    "method": c["cipher"],
                    "password": c["password"],
                    "udp": c.get("udp", False),
                }
            ]
        },
    }
    _add_stream(node, ob)
    return ob

@register("vmess")
def convert_vmess(node: Dict) -> Dict:
    c = node["config"]
    ob = {
        "tag": node["tag"],
        "protocol": "vmess",
        "settings": {
            "vnext": [
                {
                    "address": c["server"],
                    "port": c["port"],
                    "users": [{"id": c["uuid"], "alterId": c.get("alter_id", 0)}],
                }
            ]
        },
    }
    _add_stream(node, ob)
    return ob

@register("vless")
def convert_vless(node: Dict) -> Dict:
    c = node["config"]
    user: Dict = {"id": c["uuid"]}
    if c.get("flow"):
        user["flow"] = c["flow"]
    ob = {
        "tag": node["tag"],
        "protocol": "vless",
        "settings": {
            "vnext": [
                {"address": c["server"], "port": c["port"], "users": [user]}
            ]
        },
    }
    _add_stream(node, ob)
    return ob

@register("trojan")
def convert_trojan(node: Dict) -> Dict:
    c = node["config"]
    ob = {
        "tag": node["tag"],
        "protocol": "trojan",
        "settings": {
            "servers": [
                {
                    "address": c["server"],
                    "port": c["port"],
                    "password": c["password"],
                }
            ]
        },
    }
    _add_stream(node, ob)
    return ob

@register("hysteria")
@register("hysteria2")
def convert_hysteria(node: Dict) -> Dict:
    c = node["config"]
    ob = {
        "tag": node["tag"],
        "protocol": node["type"],
        "settings": {
            "servers": [
                {
                    "address": c["server"],
                    "port": c["port"],
                    "password": c["password"],
                }
            ]
        },
    }
    _add_stream(node, ob)
    return ob

@register("tuic")
def convert_tuic(node: Dict) -> Dict:
    c = node["config"]
    ob = {
        "tag": node["tag"],
        "protocol": "tuic",
        "settings": {
            "servers": [
                {
                    "address": c["server"],
                    "port": c["port"],
                    "password": c["password"],
                    "uuid": c["uuid"],
                    "congestion_control": c.get("congestion_control"),
                    "udp_relay_mode": c.get("udp_relay_mode"),
                    "alpn": c.get("alpn"),
                }
            ]
        },
    }
    _add_stream(node, ob)
    return ob

# ───────────────────── file helpers ──────────────────────────

def load_nodes(path: Path) -> List[Dict]:
    data = json.loads(path.read_text())
    if not isinstance(data, list):
        logger.error("Node file must be a JSON array.")
        raise ValueError("Node file must be a JSON array.")
    if validate and NODE_SCHEMA.exists():
        schema = json.loads(NODE_SCHEMA.read_text())
        for n in data:
            try:
                validate(instance=n, schema=schema)
            except ValidationError as e:
                logger.error(f"Validation error for node '{n.get('tag', '<unknown>')}': {e.message}")
                raise
    return data


def convert_nodes(nodes: List[Dict], workers: int = 6) -> List[Dict]:
    outbounds: List[Dict] = []
    with ThreadPoolExecutor(max_workers=workers) as exe:
        fut = {
            exe.submit(_converters[n["type"].lower()], n): n["tag"]
            for n in nodes if n.get("type", "").lower() in _converters
        }
        for f in as_completed(fut):
            try:
                outbounds.append(f.result())
            except Exception as e:
                logger.warning(f"Conversion error for node '{fut[f]}': {e}")
    return outbounds

# ──────────────────────── CLI ────────────────────────────────

if __name__ == "__main__":
    argp = argparse.ArgumentParser("node→xray converter")
    argp.add_argument("--nodes", required=True, type=Path)
    argp.add_argument("--base", type=Path)
    argp.add_argument("--out",  default=Path("xray-generated.json"), type=Path)
    opts = argp.parse_args()

    try:
        nodes = load_nodes(opts.nodes)
    except Exception as e:
        logger.error(f"Failed to load nodes file: {e}")
        sys.exit(1)
    outs = convert_nodes(nodes)

    try:
        if opts.base:
            base_cfg = json.loads(opts.base.read_text())
        else:
            base_cfg = {
                "log": {"loglevel": "warning"},
                "inbounds": [
                    {"tag": "socks", "listen": "127.0.0.1", "port": 1080, "protocol": "socks", "settings": {"auth": "noauth"}}
                ],
                "outbounds": []
            }
        base_cfg.setdefault("outbounds", []).extend(outs)
        opts.out.write_text(json.dumps(base_cfg, indent=2))
        logger.info(f"Xray config saved → {opts.out}")
    except Exception as e:
        logger.error(f"Failed to write output config: {e}")
        sys.exit(1)
