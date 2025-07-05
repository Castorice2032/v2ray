import re
import base64
import json

def decode_vmess_payload(payload):
    try:
        padded = payload + '=' * (-len(payload) % 4)
        decoded = base64.b64decode(padded).decode(errors="ignore")
        return json.loads(decoded)
    except Exception:
        return None

def parse_vmess(link):
    pattern = re.compile(r"^vmess://(.+)", re.IGNORECASE)
    m = pattern.match(link.strip())
    if not m:
        return None
    payload = m.group(1)
    data = decode_vmess_payload(payload)
    if not data:
        return None
    return {
        "raw": link.strip(),
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
