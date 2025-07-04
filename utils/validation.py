import re
import json
import base64
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from jsonschema import validate, ValidationError
import sys

# Directories
INPUT_DIR = Path(__file__).resolve().parent.parent / "data/input"
TMP_DIR = Path(__file__).resolve().parent.parent / "data/tmp"
LOG_DIR = Path(__file__).resolve().parent.parent / "data/logs"
SCHEMA_DIR = Path(__file__).resolve().parent.parent / "config"
TMP_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Load schema
for fname in SCHEMA_DIR.iterdir():
    if fname.name.strip().startswith("schema") and fname.name.strip().endswith(".json"):
        SCHEMA_PATH = fname
        break
else:
    raise FileNotFoundError("No schema json found in config/")

with open(SCHEMA_PATH, encoding="utf-8") as f:
    SCHEMA = json.load(f)

PATTERNS = {
    "ss": re.compile(r"^ss://([^@]+)@([\w\.-]+):(\d+)", re.IGNORECASE),
    "vmess": re.compile(r"^vmess://(.+)", re.IGNORECASE),
    "vless": re.compile(r"^vless://([^@]+)@([\w\.-]+):(\d+)", re.IGNORECASE),
    "trojan": re.compile(r"^trojan://([^@]+)@([\w\.-]+):(\d+)", re.IGNORECASE),
    "hysteria2": re.compile(r"^hysteria2://(.+)", re.IGNORECASE),
    "hysteria": re.compile(r"^hysteria://(.+)", re.IGNORECASE),
}

def decode_vmess_payload(payload):
    try:
        padded = payload + '=' * (-len(payload) % 4)
        decoded = base64.b64decode(padded).decode(errors="ignore")
        return json.loads(decoded)
    except Exception:
        return None

def parse_node(proto, line):
    line = line.strip()
    if proto == "ss":
        m = PATTERNS["ss"].match(line)
        if m:
            userinfo, server, port = m.groups()
            try:
                userinfo_dec = base64.urlsafe_b64decode(userinfo + '=' * (-len(userinfo) % 4)).decode(errors="ignore")
                cipher, password = userinfo_dec.split(":", 1)
            except Exception:
                cipher, password = "", ""
            return {
                "raw": line,
                "tag": f"ss-{server}-{port}",
                "type": "ss",
                "config": {
                    "type": "ss",
                    "server": server,
                    "port": int(port),
                    "cipher": cipher,
                    "password": password
                },
                "meta": {}
            }
    elif proto == "vmess":
        m = PATTERNS["vmess"].match(line)
        if m:
            payload = m.group(1)
            data = decode_vmess_payload(payload)
            if not data:
                return None
            return {
                "raw": line,
                "tag": f"vmess-{data.get('add','')}-{data.get('port','')}",
                "type": "vmess",
                "config": {
                    "type": "vmess",
                    "server": data.get("add", ""),
                    "port": int(data.get("port", 0)),
                    "uuid": data.get("id", ""),
                    "alter_id": int(data.get("aid", 0)),
                    "tls": {"enabled": data.get("tls", "") == "tls", "sni": data.get("sni", ""), "insecure": False},
                    "transport": {"type": data.get("net", "none"), "path": data.get("path", ""), "host": data.get("host", "")}
                },
                "meta": {}
            }
    elif proto == "vless":
        m = PATTERNS["vless"].match(line)
        if m:
            uuid, server, port = m.groups()
            return {
                "raw": line,
                "tag": f"vless-{server}-{port}",
                "type": "vless",
                "config": {
                    "type": "vless",
                    "server": server,
                    "port": int(port),
                    "uuid": uuid,
                    "flow": "",
                    "tls": {"enabled": False},
                    "transport": {"type": "none"}
                },
                "meta": {}
            }
    elif proto == "trojan":
        m = PATTERNS["trojan"].match(line)
        if m:
            password, server, port = m.groups()
            return {
                "raw": line,
                "tag": f"trojan-{server}-{port}",
                "type": "trojan",
                "config": {
                    "type": "trojan",
                    "server": server,
                    "port": int(port),
                    "password": password,
                    "tls": {"enabled": True}
                },
                "meta": {}
            }
    elif proto in ("hysteria2", "hysteria"):
        m = PATTERNS[proto].match(line)
        if m:
            raw = m.group(1)
            try:
                passw, rest = raw.split("@", 1)
                server, port = rest.split(":", 1)
                port = int(port.split("?")[0])
            except Exception:
                passw, server, port = "", "", 0
            return {
                "raw": line,
                "tag": f"hysteria2-{server}-{port}",
                "type": "hysteria2",
                "config": {
                    "type": "hysteria2",
                    "server": server,
                    "port": int(port),
                    "password": passw,
                    "tls": {"enabled": True, "insecure": False}
                },
                "meta": {}
            }
    return None

def process_line(proto, idx, line):
    node = parse_node(proto, line)
    if not node:
        return {"ok": False, "line": idx, "reason": "parse_failed", "link": line.strip()}
    try:
        validate(instance=node, schema=SCHEMA)
        return {"ok": True, "json": node, "line": idx}
    except ValidationError as e:
        return {"ok": False, "line": idx, "reason": e.message, "link": line.strip()}

def process_file(proto):
    txt_path = INPUT_DIR / f"{proto}.txt"
    if not txt_path.exists():
        return
    tmp_path = TMP_DIR / f"{proto}.jsonl"
    log_path = LOG_DIR / f"bad_{proto}.log"
    with open(txt_path, encoding="utf-8") as f:
        lines = f.readlines()
    total = len(lines)
    valid = 0
    bad = 0
    results = [None] * total
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(process_line, proto, idx+1, line): idx for idx, line in enumerate(lines)}
        last_log = time.time()
        for i, future in enumerate(as_completed(futures)):
            idx = futures[future]
            res = future.result()
            results[idx] = res
            if res["ok"]:
                valid += 1
            else:
                bad += 1
            # Progress bar
            if time.time() - last_log > 0.05 or i == total-1:
                bar_len = 30
                filled = int(bar_len * (i+1) / total) if total else 0
                bar = "█" * filled + "-" * (bar_len - filled)
                sys.stdout.write(f"\r[{bar}] {i+1}/{total} | valid: {valid} | bad: {bad}")
                sys.stdout.flush()
                last_log = time.time()
    print()
    # Write valid jsons
    with open(tmp_path, "w", encoding="utf-8") as outf:
        for res in results:
            if res and res["ok"]:
                outf.write(json.dumps(res["json"], ensure_ascii=False) + "\n")
    # Write bad logs
    with open(log_path, "w", encoding="utf-8") as logf:
        for res in results:
            if res and not res["ok"]:
                logf.write(json.dumps(res, ensure_ascii=False) + "\n")
    print(f"✅ {proto}: {valid} valid, {bad} bad | tmp: {tmp_path.name} | log: {log_path.name}")

def main():
    for proto in PATTERNS.keys():
        process_file(proto)
    print("\n📊 Validation finished. Check tmp/ and logs/ for results.")

if __name__ == "__main__":
    main()
