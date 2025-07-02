# -*- coding: utf-8 -*-
"""
convert_and_test.py  (v2.0 – ICMP و TCP پینگ)
=============================================

این نسخه بدون نیاز به Sing‑Box، برای هر سرور در `configs.txt` **دو نوع پینگ** می‌سنجد:

1. **ICMP (ping معمولی)** → ستون `icmp_ms`
2. **TCP handshake** در همان پورتی که در لینک آمده → ستون `tcp_ms`

خروجی `report.json` به‌صورت لیست دیکشنری است:
```json
[
  {
    "tag": "hysteria-udp-us-...",
    "icmp_ms": 87,
    "tcp_ms": 123
  },
  ...
]
```
اگر یک تست ناموفق باشد، مقدار آن `null` می‌شود و پیام خطا در `error` نوشته می‌شود.

پیش‌نیازها:
- Linux/macOS: ابزار `ping`
- Python 3.9+
"""

import json
import re
import socket
import subprocess
import time
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional

CONFIG_TXT = Path("configs.txt")
REPORT_JSON = Path("report.json")

# ------------------------- Parsers ------------------------- #

def url_to_server_port_tag(link: str, idx: int) -> Dict[str, str]:
    """برگرداندن host, port, tag از لینک hysteria/hy2."""
    scheme = "hysteria://" if link.startswith("hysteria://") else "hy2://"
    body = link.split(scheme, 1)[1]

    if "#" in body:
        body, human_tag = body.split("#", 1)
    else:
        human_tag = f"srv-{idx}"

    if "?" in body:
        host_port, _ = body.split("?", 1)
    else:
        host_port = body

    if ":" not in host_port:
        raise ValueError(f"لینک بدون پورت: {link}")
    host, port = host_port.split(":", 1)

    tag = re.sub(r"\W+", "-", human_tag).strip("-").lower() or f"srv-{idx}"
    return {"host": host, "port": int(port), "tag": tag}


def parse_configs(path: Path) -> List[Dict[str, str]]:
    out = []
    for idx, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        ln = raw.strip()
        if ln and not ln.startswith("#") and ln.startswith(("hysteria://", "hy2://")):
            out.append(url_to_server_port_tag(ln, idx))
    if not out:
        raise RuntimeError("هیچ لینک hysteria یا hy2 پیدا نشد!")
    return out

# ------------------------- Ping Helpers ------------------------- #

def icmp_ping(host: str, count: int = 2, timeout: int = 3) -> Optional[int]:
    try:
        out = subprocess.check_output(["ping", "-c", str(count), "-w", str(timeout), host], text=True)
        m = re.search(r"min/avg/max/.+ = [\d.]+/([\d.]+)/", out)
        if m:
            return round(float(m.group(1)))
    except Exception:
        return None
    return None


def tcp_ping(host: str, port: int, timeout: float = 3.0) -> Optional[int]:
    try:
        t0 = time.perf_counter()
        with socket.create_connection((host, port), timeout=timeout):
            return int((time.perf_counter() - t0) * 1000)
    except Exception:
        return None

# --------------------------- main --------------------------- #
if __name__ == "__main__":
    if not CONFIG_TXT.exists():
        raise SystemExit("configs.txt پیدا نشد!")

    servers = parse_configs(CONFIG_TXT)
    print(f"[+] {len(servers)} سرور پیدا شد. در حال پینگ …")

    results: List[Dict] = []
    for s in servers:
        print(f"• {s['tag']} ({s['host']}:{s['port']}) …", end=" ")
        icmp = icmp_ping(s["host"])  # ICMP
        tcp = tcp_ping(s["host"], s["port"])  # TCP handshake
        status = {
            "tag": s["tag"],
            "host": s["host"],
            "port": s["port"],
            "icmp_ms": icmp,
            "tcp_ms": tcp,
        }
        print(f"icmp={icmp}ms, tcp={tcp}ms")
        results.append(status)

    REPORT_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[✓] نتایج در {REPORT_JSON} ذخیره شد.")
