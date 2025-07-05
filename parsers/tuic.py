import re

def parse_tuic(link):
    pattern = re.compile(r"^tuic://([^@]+)@([\w\.-]+):(\d+)", re.IGNORECASE)
    m = pattern.match(link.strip())
    if not m:
        return None
    password, server, port = m.groups()
    return {
        "raw": link.strip(),
        "tag": f"tuic-{server}-{port}",
        "type": "tuic",
        "config": {
            "type": "tuic",
            "server": server,
            "port": int(port),
            "password": password,
            "tls": {"enabled": True}
        },
        "meta": {}
    }
