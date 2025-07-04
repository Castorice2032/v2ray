#!/usr/bin/env python3
# convert_signbox_to_links.py
# Python ≥3.8

import json, base64, sys, pathlib, urllib.parse, warnings

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # YAML پشتیبانی نمی‌شود مگر اینکه pyyaml نصب کنید


def b64url(data: str) -> str:
    """Base64-URL بدون padding"""
    out = base64.urlsafe_b64encode(data.encode()).decode()
    return out.rstrip("=")


def crit(node, *keys):
    """دریافت مقدار کلیدهای حیاتی یا برگرداندن None اگر وجود نداشته باشد"""
    try:
        return [node[k] for k in keys]
    except KeyError:
        return None


def ss_link(node):
    vals = crit(node, "method", "password", "server")
    if not vals:
        return None
    method, password, server = vals
    port = node.get("server_port") or node.get("port")
    if not port:
        return None
    userinfo = f"{method}:{password}@{server}:{port}"
    tag = urllib.parse.quote(node.get("tag", "ss"))
    return f"ss://{b64url(userinfo)}#{tag}"


def trojan_link(node):
    vals = crit(node, "password", "server")
    if not vals:
        return None
    password, server = vals
    port = node.get("server_port") or node.get("port")
    if not port:
        return None
    tag = urllib.parse.quote(node.get("tag", "trojan"))
    return f"trojan://{password}@{server}:{port}#{tag}"


def vless_link(node):
    vals = crit(node, "uuid", "server")
    if not vals:
        return None
    uuid, server = vals
    port = node.get("server_port") or node.get("port")
    if not port:
        return None
    tag = urllib.parse.quote(node.get("tag", "vless"))
    return f"vless://{uuid}@{server}:{port}#{tag}"


def hysteria2_link(node):
    server = node.get("server")
    port = node.get("server_port") or node.get("port")
    if not (server and port):
        return None
    pwd = node.get("password") or node.get("auth_str") or ""
    tag = urllib.parse.quote(node.get("tag", "hysteria2"))
    return f"hysteria2://{pwd}@{server}:{port}?insecure=1#{tag}"


def vmess_link(node):
    vals = crit(node, "uuid", "server")
    if not vals:
        return None
    uuid, server = vals
    port = node.get("server_port") or node.get("port")
    if not port:
        return None
    vmess_obj = {
        "v": "2",
        "ps": node.get("tag", "vmess"),
        "add": server,
        "port": str(port),
        "id": uuid,
        "aid": "0",
        "net": node.get("network", "tcp"),
        "type": "none",
        "host": "",
        "path": node.get("transport", {}).get("path", ""),
        "tls": "tls" if node.get("tls", {}).get("enabled") else ""
    }
    return "vmess://" + b64url(json.dumps(vmess_obj, separators=(',', ':')))


HANDLERS = {
    "shadowsocks": ss_link, "ss": ss_link,
    "trojan": trojan_link,
    "vless": vless_link,
    "hysteria2": hysteria2_link,
    "vmess": vmess_link,
}


def load_config(path: pathlib.Path):
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        if yaml:
            return yaml.safe_load(text)
        raise RuntimeError("فایل نه JSON معتبر است نه YAML.")


def convert(in_file: pathlib.Path, out_file: pathlib.Path):
    cfg = load_config(in_file)
    outbounds = cfg.get("outbounds", [])
    links = []

    for idx, node in enumerate(outbounds, 1):
        kind = node.get("type")
        handler = HANDLERS.get(kind)
        if not handler:
            warnings.warn(f"[{idx}] نوع ناشناخته یا پشتیبانی‌نشده: {kind}")
            continue
        link = handler(node)
        if link:
            links.append(link)
        else:
            warnings.warn(f"[{idx}] نود {kind} به‌دلیل کمبود کلیدهای حیاتی رد شد.")

    out_file.write_text("\n".join(links), encoding="utf-8")

    if links:
        print(f"✅ {len(links)} لینک ساخته شد → {out_file}")
    else:
        print("⚠️  هیچ لینکی ساخته نشد!  کلیدهای فایل یا نوع نودها را بررسی کنید.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_signbox_to_links.py singbox.json [tmps.txt]")
        sys.exit(1)

    in_path = pathlib.Path(sys.argv[1]).expanduser()
    out_path = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "tmps.txt").expanduser()
    convert(in_path, out_path)
