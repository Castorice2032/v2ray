import re

def parse_vless(link):
    pattern = re.compile(r"^vless://([^@]+)@([\w\.-]+):(\d+)", re.IGNORECASE)
    m = pattern.match(link.strip())
    if not m:
        return None
    uuid, server, port = m.groups()
    return {
        "raw": link.strip(),
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
