import os
import json
import base64
import re
import socket
import time
from pathlib import Path
from collections import defaultdict
from datetime import datetime

"""
Enhanced proxy‑analyser with:
• real‑time incremental saving (alive.json, dead.json)
• dead / alive separation + full report
• summary log with timestamp & counts (updates every batch)
• resume capability (state saved in tmp)
• designed for long‑running tasks (can be resumed by GitHub Action cron)
"""

# ───────── paths ─────────
BASE_DIR   = Path(__file__).resolve().parent.parent
IN_DIR     = (BASE_DIR / "data/input").resolve()
OUT_DIR    = (BASE_DIR / "data/output").resolve()
LOG_DIR    = (BASE_DIR / "data/logs").resolve()
TMP_DIR    = (BASE_DIR / "data/tmp").resolve()

for p in (OUT_DIR, LOG_DIR, TMP_DIR):
    p.mkdir(parents=True, exist_ok=True)

STATE_F     = TMP_DIR  / "analyze_state.json"
ALIVE_F     = OUT_DIR / "alive.json"
DEAD_F      = OUT_DIR / "dead.json"
FULL_F      = OUT_DIR / "servers_report.json"
SUMMARY_F   = LOG_DIR / "summary_report.json"

# batch size for interim writes
SAVE_EVERY = 20

PROTOCOL_MAP = {
    'vmess.txt':  'vmess',
    'vless.txt':  'vless',
    'ss.txt':     'shadowsocks',
    'trojan.txt': 'trojan',
    'hysteria.txt':'hysteria',
}
PATTERNS = {
    'vmess':  re.compile(r'@([\w\.-]+)'),
    'vless':  re.compile(r'@([\w\.-]+)'),
    'trojan': re.compile(r'@([\w\.-]+)'),
    'hysteria': re.compile(r'@([\w\.-]+)'),
    'shadowsocks': re.compile(r'@([\w\.-]+):'),
}

REGIONS = [
  'iran','us','uk','germany','france','turkey','nl','ru','uae',
  'singapore','japan','korea','canada','india','australia','de'
]

# ───────── utils ─────────

def load_state():
    if STATE_F.exists():
        return json.loads(STATE_F.read_text())
    return {"done": []}

def save_state(done_links):
    STATE_F.write_text(json.dumps({"done": list(done_links)}, ensure_ascii=False))

def extract_info(link:str, proto:str):
    m = PATTERNS[proto].search(link)
    host = m.group(1) if m else None
    tag  = re.search(r'#(.+)$', link)
    name = tag.group(1) if tag else host or proto
    region = None
    for r in REGIONS:
        if r in name.lower():
            region = r
            break
    return name, host, region

def ping(host:str, timeout=2):
    if not host:
        return None
    try:
        start = time.perf_counter()
        socket.create_connection((host,443), timeout=timeout).close()
        return int((time.perf_counter()-start)*1000)
    except Exception:
        return None

# ───────── main logic ─────────

def analyse(batch_sleep:float|None=None):
    # collect links
    all_links=[]
    for file,proto in PROTOCOL_MAP.items():
        p=IN_DIR/file
        if p.exists():
            for ln in p.read_text().splitlines():
                ln=ln.strip()
                if ln and not ln.startswith('#'):
                    all_links.append((ln,proto))
    total=len(all_links)
    if total==0:
        print("No links found in input directory.");return

    # resume
    state=load_state();done=set(state['done'])
    alive,dead=[],[]
    if ALIVE_F.exists():
        alive=json.loads(ALIVE_F.read_text())
    if DEAD_F.exists():
        dead=json.loads(DEAD_F.read_text())

    processed= len(done)
    for idx,(link,proto) in enumerate(all_links,1):
        if link in done: continue
        name,host,region=extract_info(link,proto)
        latency=ping(host)
        item={"name":name,"protocol":proto,"ping":latency,"status":"alive" if latency else "dead","region":region,"link":link}
        (alive if latency else dead).append(item)
        done.add(link)
        processed+=1
        # progress bar
        pct=int(processed/total*100)
        bar='█'*(pct//4)+'-'*(25-pct//4)
        print(f"\r[{bar}] {processed}/{total} {name} {proto} {latency if latency else 'Timeout'} ",end='')

        if processed % SAVE_EVERY==0:
            ALIVE_F.write_text(json.dumps(alive,ensure_ascii=False))
            DEAD_F.write_text(json.dumps(dead,ensure_ascii=False))
            save_state(done)
            update_summary(alive,dead,total)
            if batch_sleep:
                time.sleep(batch_sleep)

    # final save
    ALIVE_F.write_text(json.dumps(alive,ensure_ascii=False,indent=2))
    DEAD_F.write_text(json.dumps(dead,ensure_ascii=False,indent=2))
    FULL_F.write_text(json.dumps(alive+dead,ensure_ascii=False,indent=2))
    save_state(done)
    update_summary(alive,dead,total)
    print("\n✅ analysis finished.")


def update_summary(alive,dead,total):
    proto_stat=defaultdict(lambda:{"alive":0,"dead":0})
    for itm in alive:
        proto_stat[itm['protocol']]['alive']+=1
    for itm in dead:
        proto_stat[itm['protocol']]['dead']+=1
    summary={
        "generated_at":datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "total_links":total,
        "alive":len(alive),
        "dead":len(dead),
        "per_protocol":proto_stat
    }
    SUMMARY_F.write_text(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':
    # batch_sleep=5 will sleep 5s every SAVE_EVERY links to stay alive on free runners
    analyse(batch_sleep=None)
