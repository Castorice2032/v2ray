import os
import json
import base64
import re
import socket
import time
import argparse
from pathlib import Path
from collections import defaultdict
from datetime import datetime

"""
Proxy analyser (resume + real‑time save + safe JSON read).
Outputs:
  • data/output/alive.json   : live servers
  • data/output/dead.json    : dead servers
  • data/logs/analyze_report.json : summary (total / per‑protocol / timestamp)
Usage:
  python utils/analyze.py            # run normally
  python utils/analyze.py --sleep 5  # sleep 5s every batch
"""

# ───────── paths ─────────
BASE_DIR   = Path(__file__).resolve().parent.parent
IN_DIR     = BASE_DIR / "data/input"
OUT_DIR    = BASE_DIR / "data/output"
LOG_DIR    = BASE_DIR / "data/logs"
TMP_DIR    = BASE_DIR / "data/tmp"
for p in (OUT_DIR, LOG_DIR, TMP_DIR):
    p.mkdir(parents=True, exist_ok=True)

STATE_F   = TMP_DIR / "analyze_state.json"
ALIVE_F   = OUT_DIR / "alive.json"
DEAD_F    = OUT_DIR / "dead.json"
REPORT_F  = LOG_DIR / "analyze_report.json"

SAVE_EVERY = 20  # save every N links

PROTOCOL_MAP = {
    'vmess.txt':  'vmess',
    'vless.txt':  'vless',
    'ss.txt':     'shadowsocks',
    'trojan.txt': 'trojan',
    'hysteria.txt':'hysteria',
}
PATTERNS = {
    'vmess':       re.compile(r'@([\w\.-]+)'),
    'vless':       re.compile(r'@([\w\.-]+)'),
    'trojan':      re.compile(r'@([\w\.-]+)'),
    'hysteria':    re.compile(r'@([\w\.-]+)'),
    'shadowsocks': re.compile(r'@([\w\.-]+):'),
}
REGIONS = [
  'iran','us','uk','germany','france','turkey','nl','ru','uae',
  'singapore','japan','korea','canada','india','australia','de'
]

# ───────── helpers ─────────

def _safe_json_read(path: Path, default):
    """Read JSON safely; if file empty or malformed → default."""
    try:
        if path.exists() and path.stat().st_size > 0:
            return json.loads(path.read_text())
    except json.JSONDecodeError:
        pass
    return default

def load_state():
    return _safe_json_read(STATE_F, {"done": []})

def save_state(done):
    STATE_F.write_text(json.dumps({"done": list(done)}, ensure_ascii=False))

def extract(link: str, proto: str):
    host = None
    m = PATTERNS[proto].search(link)
    if m:
        host = m.group(1)
    tag = re.search(r'#(.+)$', link)
    name = tag.group(1) if tag else host or proto
    region = next((r for r in REGIONS if r in name.lower()), None)
    return name, host, region

def tcp_ping(host: str, timeout=2):
    if not host:
        return None
    try:
        start = time.perf_counter()
        socket.create_connection((host, 443), timeout=timeout).close()
        return int((time.perf_counter() - start) * 1000)
    except Exception:
        return None

# ───────── analysis ─────────

def analyse(batch_sleep=None):
    # gather links
    links = []
    for fname, proto in PROTOCOL_MAP.items():
        f = IN_DIR / fname
        if f.exists():
            for line in f.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    links.append((line, proto))
    total = len(links)
    if not total:
        print("❌ No links found in data/input"); return

    # resume
    state = load_state()
    done  = set(state["done"])
    alive = _safe_json_read(ALIVE_F, [])
    dead  = _safe_json_read(DEAD_F,  [])

    processed = len(done)
    for idx, (link, proto) in enumerate(links, 1):
        if link in done:
            continue
        name, host, region = extract(link, proto)
        lat = tcp_ping(host)
        item = {
            "name": name,
            "protocol": proto,
            "ping": lat,
            "link": link,
            "region": region,
            "status": "alive" if lat is not None else "dead"
        }
        (alive if lat is not None else dead).append(item)
        done.add(link)
        processed += 1

        # progress bar
        pct = int(processed / total * 100)
        bar = '█' * (pct // 4) + '-' * (25 - pct // 4)
        print(f"\r[{bar}] {processed}/{total} {name} {proto} {lat if lat else 'Timeout'} ", end='')

        if processed % SAVE_EVERY == 0:
            _flush(alive, dead, done, total)
            if batch_sleep:
                time.sleep(batch_sleep)

    _flush(alive, dead, done, total)
    print("\n✅ Analysis finished.")


def _flush(alive, dead, done, total):
    ALIVE_F.write_text(json.dumps(alive, ensure_ascii=False, indent=2))
    DEAD_F.write_text(json.dumps(dead, ensure_ascii=False, indent=2))
    save_state(done)
    _update_summary(alive, dead, total)


def _update_summary(alive, dead, total):
    stats = defaultdict(lambda: {"alive": 0, "dead": 0})
    for i in alive:
        stats[i['protocol']]['alive'] += 1
    for i in dead:
        stats[i['protocol']]['dead'] += 1
    report = {
        "last_update": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
        "total_links": total,
        "alive": len(alive),
        "dead": len(dead),
        "per_protocol": stats
    }
    REPORT_F.write_text(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze proxy links (resume + real‑time save)")
    parser.add_argument("--sleep", type=float, default=None, help="seconds to sleep between batches (SAVE_EVERY)")
    args = parser.parse_args()
    analyse(batch_sleep=args.sleep)
