import re

def parse_hysteria(link):
    pattern = re.compile(r"^hysteria://(.+)", re.IGNORECASE)
    m = pattern.match(link.strip())
    if not m:
        return None
    raw = m.group(1)
    try:
        passw, rest = raw.split("@", 1)
        server, port = rest.split(":", 1)
        port = int(port.split("?")[0])
    except Exception:
        passw, server, port = "", "", 0
    return {
        "raw": link.strip(),
        "tag": f"hysteria-{server}-{port}",
        "type": "hysteria",
        "config": {
            "type": "hysteria",
            "server": server,
            "port": int(port),
            "password": passw,
            "tls": {"enabled": True, "insecure": False}
        },
        "meta": {}
    }
