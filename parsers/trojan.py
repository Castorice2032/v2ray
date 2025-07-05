import re

def parse_trojan(link):
    pattern = re.compile(r"^trojan://([^@]+)@([\w\.-]+):(\d+)", re.IGNORECASE)
    m = pattern.match(link.strip())
    if not m:
        return None
    password, server, port = m.groups()
    return {
        "raw": link.strip(),
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
