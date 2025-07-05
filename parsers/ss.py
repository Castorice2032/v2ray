import re
import base64

def parse_ss(link):
    pattern = re.compile(r"^ss://([^@]+)@([\w\.-]+):(\d+)", re.IGNORECASE)
    m = pattern.match(link.strip())
    if not m:
        return None
    userinfo, server, port = m.groups()
    try:
        userinfo_dec = base64.urlsafe_b64decode(userinfo + '=' * (-len(userinfo) % 4)).decode(errors="ignore")
        cipher, password = userinfo_dec.split(":", 1)
    except Exception:
        cipher, password = "", ""
    return {
        "raw": link.strip(),
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
