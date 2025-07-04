#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proxy Collector & Reporter
=========================

This script recursively fetches proxy subscription files, extracts individual
proxy links, and produces per‑protocol text files plus a detailed JSON report.

Supported input formats (auto‑detected):

| Type keyword          | Extension          | Description                                             |
|-----------------------|--------------------|---------------------------------------------------------|
| **subscription_plain**| (none)             | Raw or Base64‑encoded list (ss:// …)                    |
| **clash_yaml**        | .yaml / .yml       | Clash config containing a `proxies:` array              |
| **singbox_json**      | .json              | Sing‑box config; relevant proxies live in `outbounds`   |
| *(fallback)*          | any                | Treated as plain text; every line scanned for patterns  |

Nested `url` or `path` keys inside YAML/JSON are queued and processed, enabling
fully recursive crawling from a single master URL.

Outputs
-------
* **data/input/<proto>.txt** – one file per protocol (ss, vmess, vless, trojan, …)
* **data/input/report.json** – timestamped report with totals + child counts
"""

import json
import base64
import re
import yaml
import requests
from collections import defaultdict
from pathlib import Path
from datetime import datetime

# ─── Paths ───────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent
INPUT_DIR   = (BASE_DIR / "../data/input").resolve()
LOG_DIR     = (BASE_DIR / "../data/logs").resolve()
JSON_DIR    = (BASE_DIR / "../data/json").resolve()

INPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
JSON_DIR.mkdir(parents=True, exist_ok=True)

TYPE_JSON   = JSON_DIR / "urls_type.json"     # input list
OUTPUT_DIR  = INPUT_DIR                       # proxy txt files go here
REPORT_JSON = INPUT_DIR / "report.json"       # final report

# ─── Patterns ────────────────────────────────────────────────────────────
PATTERNS = {
    "ss":       re.compile(r"^ss://.+",          re.MULTILINE),
    "vmess":    re.compile(r"^vmess://.+",       re.MULTILINE),
    "vless":    re.compile(r"^vless://.+",       re.MULTILINE),
    "trojan":   re.compile(r"^trojan://.+",      re.MULTILINE),
    "hysteria": re.compile(r"^hysteria2?://.+",  re.MULTILINE),
    "reality":  re.compile(r"^reality://.+",     re.MULTILINE),
    "http":     re.compile(r"^https?://.+",      re.MULTILINE),  # catch child URLs
}

# ─── Helpers ─────────────────────────────────────────────────────────────

def guess_type(url: str, default: str = "subscription_plain") -> str:
    """Guess file type from URL extension."""
    if url.endswith((".yaml", ".yml")):
        return "clash_yaml"
    if url.endswith(".json"):
        return "singbox_json"
    return default


def find_urls(obj) -> set[str]:
    """Recursively collect all string fields called 'url' or 'path'."""
    found: set[str] = set()

    def dig(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("url", "path") and isinstance(v, str) and v.startswith(("http://", "https://")):
                    found.add(v.strip())
                dig(v)
        elif isinstance(o, list):
            for itm in o:
                dig(itm)

    dig(obj)
    return found


def extract_links(text: str):
    links: defaultdict[str, list[str]] = defaultdict(list)
    for line in text.splitlines():
        line = line.strip()
        for proto, pat in PATTERNS.items():
            if pat.match(line):
                links[proto].append(line)
                break
    return links


def extract_from_clash_yaml(text: str):
    links: defaultdict[str, list[str]] = defaultdict(list)
    extra: set[str] = set()
    try:
        data = yaml.safe_load(text)
        for proxy in data.get("proxies", []):
            ptype = proxy.get("type")
            if ptype == "ss":
                userinfo = f"{proxy.get('cipher','')}:{proxy.get('password','')}"
                b64 = base64.urlsafe_b64encode(userinfo.encode()).decode().rstrip("=")
                links["ss"].append(f"ss://{b64}@{proxy.get('server')}:{proxy.get('port')}")
            elif ptype == "vmess":
                vm_b64 = base64.urlsafe_b64encode(json.dumps(proxy).encode()).decode().rstrip("=")
                links["vmess"].append(f"vmess://{vm_b64}")
            elif ptype == "vless":
                links["vless"].append(f"vless://{proxy.get('uuid')}@{proxy.get('server')}:{proxy.get('port')}")
            elif ptype == "trojan":
                links["trojan"].append(f"trojan://{proxy.get('password')}@{proxy.get('server')}:{proxy.get('port')}")
        extra |= find_urls(data)
    except Exception:
        pass
    return links, extra


def extract_from_singbox_json(text: str):
    links: defaultdict[str, list[str]] = defaultdict(list)
    extra: set[str] = set()
    try:
        data = json.loads(text)
        for ob in data.get("outbounds", []):
            otype = ob.get("type")
            server = ob.get("server")
            port   = ob.get("server_port") or ob.get("port")
            if not server or not port:
                continue
            if otype == "shadowsocks":
                userinfo = f"{ob.get('method','')}:{ob.get('password','')}"
                b64 = base64.urlsafe_b64encode(userinfo.encode()).decode().rstrip("=")
                links["ss"].append(f"ss://{b64}@{server}:{port}")
            elif otype == "vmess":
                vm_b64 = base64.urlsafe_b64encode(json.dumps(ob).encode()).decode().rstrip("=")
                links["vmess"].append(f"vmess://{vm_b64}")
            elif otype == "vless":
                links["vless"].append(f"vless://{ob.get('uuid')}@{server}:{port}")
            elif otype == "trojan":
                links["trojan"].append(f"trojan://{ob.get('password')}@{server}:{port}")
        extra |= find_urls(data)
    except Exception:
        pass
    return links, extra


def fetch(url: str) -> str:
    r = requests.get(url, timeout=30, headers={
        "User-Agent": "Mozilla/5.0 (proxy-collector)"
    })
    r.raise_for_status()
    return r.text

# ─── Main ────────────────────────────────────────────────────────────────

def main():
    if not TYPE_JSON.exists():
        print(f"❌ {TYPE_JSON} not found")
        return

    type_list = json.loads(TYPE_JSON.read_text(encoding="utf-8"))

    all_links: defaultdict[str, list[str]] = defaultdict(list)
    report_entries: dict = {}
    queue: list[tuple[str, str]] = []
    seen: set[str] = set()

    for item in type_list:
        if item.get("type") != "error":
            queue.append((item["url"], item.get("type", "unknown")))

    while queue:
        url, typ = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)

        try:
            content = fetch(url)
            links, extra = defaultdict(list), set()

            if typ.startswith("subscription"):
                decoded = None
                try:
                    decoded = base64.b64decode(content).decode(errors="ignore")
                except Exception:
                    pass
                links = extract_links(decoded or content)

            elif typ == "clash_yaml":
                links, extra = extract_from_clash_yaml(content)

            elif typ == "singbox_json":
                links, extra = extract_from_singbox_json(content)

            else:
                links = extract_links(content)

            # process links
            for proto, lst in links.items():
                if proto == "http":
                    for u in lst:
                        if u not in seen:
                            queue.append((u, guess_type(u)))
                else:
                    all_links[proto].extend(lst)

            report_entries[url] = {
                "type": typ,
                "total": sum(len(v) for p, v in links.items() if p != "http"),
                "children": len(extra) + len(links.get("http", [])),
                "per_protocol": {p: len(lst) for p, lst in links.items() if p != "http" and lst},
            }

            for ex in extra:
                if ex not in seen:
                    queue.append((ex, guess_type(ex)))

        except Exception as e:
            report_entries[url] = {"type": typ, "error": str(e)}

    # save proxies
    for proto, lst in all_links.items():
        if proto == "http":
            continue  # not proxy links
        (OUTPUT_DIR / f"{proto}.txt").write_text("\n".join(lst), encoding="utf-8")

    header = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total_links": {p: len(v) for p, v in all_links.items() if p != "http"},
        "total_urls_processed": len(report_entries),
    }

    REPORT_JSON.write_text(
        json.dumps({**header, "items": report_entries}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"✅ Finished. Proxies saved to {OUTPUT_DIR}, report → {REPORT_JSON}")


if __name__ == "__main__":
    main()
