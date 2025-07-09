"""converters/to_xray.py

Convert a JSON array of proxy nodes (located by default at
/workspaces/v2ray/data/config.json) to a valid Xray configuration and
save the result as xray.generated.json next to the source file.

• Supported `type` values: ss | vmess | vless | trojan | hysteria |
  hysteria2 | tuic.
• TLS / stream settings are propagated when present.
• Invalid / unsupported cipher or obsolete VMess alterId>0 are skipped
  with a warning.
"""
from __future__ import annotations

import json, sys, argparse, re
from pathlib import Path
from typing import Dict, Callable, List
from concurrent.futures import ThreadPoolExecutor, as_completed

# ───────────────────────── helpers ───────────────────────────

BASE_OUTBOUND: Dict[str, str] = {
    "shadowsocks": "ss",
}  # alias map if needed

VALID_SS_CIPHERS = {
    "aes-256-gcm", "aes-128-gcm", "chacha20-ietf-poly1305",
}

_converters: Dict[str, Callable[[dict], dict]] = {}

def register(proto: str):
    def deco(fn):
        _converters[proto] = fn
        return fn
    return deco

# stream helper

def add_stream(node_cfg: dict, outbound: dict):
    cfg = node_cfg.get("config", {})
    if tls := cfg.get("tls"):
        outbound.setdefault("streamSettings", {})["security"] = (
            "tls" if tls.get("enabled") else "none"
        )
        if tls.get("enabled"):
            outbound["streamSettings"]["tlsSettings"] = {
                k: v for k, v in tls.items() if k not in {"enabled"}
            }
    if tr := cfg.get("transport"):
        net = tr.get("type", "tcp")
        outbound.setdefault("streamSettings", {})["network"] = net
        key = f"{net}Settings"
        outbound["streamSettings"][key] = {k: v for k, v in tr.items() if k != "type"}

# ───────────────────── protocol converters ───────────────────
@register("ss")
@register("shadowsocks")
def ss(node):
    c = node["config"]
    if c["cipher"] not in VALID_SS_CIPHERS:
        raise ValueError(f"cipher {c['cipher']} not supported in Xray")
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
    add_stream(node, ob)
    return ob

@register("vmess")
def vmess(node):
    c = node["config"]
    if c.get("alter_id", 0) != 0:
        raise ValueError("vmess alterId must be 0 for Xray")
    ob = {
        "tag": node["tag"],
        "protocol": "vmess",
        "settings": {
            "vnext": [
                {
                    "address": c["server"],
                    "port": c["port"],
                    "users": [{"id": c["uuid"], "alterId": 0}],
                }
            ]
        },
    }
    add_stream(node, ob)
    return ob

@register("vless")
def vless(node):
    c = node["config"]
    user = {"id": c["uuid"]}
    if c.get("flow"):
        user["flow"] = c["flow"]
    ob = {
        "tag": node["tag"],
        "protocol": "vless",
        "settings": {
            "vnext": [
                {
                    "address": c["server"],
                    "port": c["port"],
                    "users": [user],
                }
            ]
        },
    }
    add_stream(node, ob)
    return ob

@register("trojan")
def trojan(node):
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
    add_stream(node, ob)
    return ob

@register("hysteria")
@register("hysteria2")
def hysteria(node):
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
    add_stream(node, ob)
    return ob

@register("tuic")
def tuic(node):
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
                }
            ]
        },
    }
    add_stream(node, ob)
    return ob

# ───────────────────── conversion pipeline ───────────────────

def load_nodes(path: Path) -> List[dict]:
    data = json.loads(path.read_text())
    if not isinstance(data, list):
        raise ValueError("node file must be JSON array")
    return data

def convert(nodes: List[dict], workers: int = 6) -> List[dict]:
    out: List[dict] = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        fut = {ex.submit(_converters[n["type"].lower()], n): n for n in nodes if n["type"].lower() in _converters}
        for f in as_completed(fut):
            n = fut[f]
            try:
                ob = f.result()
                out.append(ob)
            except Exception as e:
                print(f"skip {n['tag']}: {e}")
    return out

# ─────────────────────────── CLI ─────────────────────────────

if __name__ == "__main__":
    p = argparse.ArgumentParser("to_xray converter")
    p.add_argument("--src", default="/workspaces/v2ray/data/config.json", type=Path, help="source nodes list")
    p.add_argument("--out", default="/workspaces/v2ray/data/xray.generated.json", type=Path)
    args = p.parse_args()

    nodes = load_nodes(args.src)
    outbounds = convert(nodes)

    xray_cfg = {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {
                "tag": "socks",
                "listen": "127.0.0.1",
                "port": 1080,
                "protocol": "socks",
                "settings": {"auth": "noauth"}
            }
        ],
        "outbounds": outbounds,
    }

    args.out.write_text(json.dumps(xray_cfg, indent=2))
    print(f"✅ saved → {args.out} ({len(outbounds)} outbounds)")
