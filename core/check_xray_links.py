#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_xray_links.py – تست سلامت لینک‌های ss://, vmess://, vless://, trojan://
خروجی:
    ▸ working.txt  → فقط لینک‌های سالم
    ▸ dead.txt     → لینک‌های خراب یا فرمت نامعتبر
"""

import base64, json, os, re, subprocess, sys, tempfile, time
from pathlib import Path
from urllib.parse import urlparse

import requests

# ─────────────── تنظیمات ───────────────
XRAY_BIN = os.path.join(os.path.dirname(__file__), "xray_core", "xray")
RAW_URL  = ("https://raw.githubusercontent.com/4n0nymou3/multi-proxy-config-"
            "fetcher/refs/heads/main/configs/proxy_configs.txt")
TEST_URL = "https://www.gstatic.com/generate_204"  # درخواست کوچکِ سریع
SOCKS_PORT = 51837                                # پورت inbounds موقّت Xray
TIMEOUT = 10                                     # ثانیه برای هر تست
# ────────────────────────────────────────


def fetch_links(url: str) -> list[str]:
    """دانلود فایل RAW و برش دادن به لینک‌های واقعی"""
    txt = requests.get(url, timeout=30).text.strip()
    tokens = re.split(r"\s+", txt)
    return [
        t for t in tokens
        if t and t[0] not in ("#", "/", "@", "🥷", ":", "👉")
    ]


def _pad_b64(s: str) -> str:
    """اضافه‌کردن = تا طول رشته مضرب ۴ شود"""
    return s + "=" * ((4 - len(s) % 4) % 4)


def build_outbound(link: str) -> dict:
    """تبدیل هر لینک به یک outbound مناسب Xray"""
    up = urlparse(link)
    tag = f"ob-{hash(link) & 0xffff:04x}"

    if up.scheme in ("ss", "shadowsocks"):
        # ss://{base64}  یا  ss://method:pwd@host:port
        if up.hostname:                       # فرمت method:pwd@host:port
            m = re.match(r"^ss://([^:]+):([^@]+)@([^:]+):(\d+)", link)
            if not m:
                raise ValueError("bad-ss-format")
            method, pwd, host, port = m.groups()
        else:                                 # فرمت base64
            plain = base64.b64decode(_pad_b64(up.netloc + up.path)).decode()
            method, rest = plain.split(":", 1)
            pwd, hostport = rest.split("@")
            host, port = hostport.split(":")
        return {
            "tag": tag,
            "protocol": "shadowsocks",
            "settings": {
                "servers": [{
                    "address": host, "port": int(port),
                    "method": method, "password": pwd, "udp": True
                }]
            },
        }

    if up.scheme == "trojan":
        m = re.match(r"^trojan://([^@]+)@([^:]+):(\d+)", link)
        if not m:
            raise ValueError("bad-trojan-format")
        pwd, host, port = m.groups()
        return {
            "tag": tag,
            "protocol": "trojan",
            "settings": {"servers": [{
                "address": host, "port": int(port), "password": pwd
            }]},
        }

    if up.scheme == "vless":
        if not (up.hostname and up.username):
            raise ValueError("bad-vless-format")
        return {
            "tag": tag,
            "protocol": "vless",
            "settings": {"vnext": [{
                "address": up.hostname,
                "port": up.port or 443,
                "users": [{"id": up.username, "encryption": "none"}],
            }]},
        }

    if up.scheme == "vmess":
        try:
            b64 = _pad_b64((up.netloc + up.path).strip("/").split("#")[0])
            raw = json.loads(base64.b64decode(b64).decode())
            return {
                "tag": tag,
                "protocol": "vmess",
                "settings": {"vnext": [{
                    "address": raw["add"],
                    "port": int(raw["port"]),
                    "users": [{
                        "id": raw["id"],
                        "alterId": int(raw.get("aid", 0)),
                        "security": raw.get("scy", "auto"),
                    }],
                }]},
            }
        except Exception as e:
            raise ValueError(f"bad-vmess-json: {e}")

    raise ValueError("unsupported-scheme")


def test_link(link: str) -> bool:
    """راه‌اندازی موقّت Xray با یک outbound و تلاش برای دسترسی به TEST_URL"""
    try:
        outbound = build_outbound(link)
    except ValueError:
        return False

    cfg = {
        "log": {"loglevel": "none"},
        "inbounds": [{
            "listen": "127.0.0.1",
            "port": SOCKS_PORT,
            "protocol": "socks",
            "settings": {},
        }],
        "outbounds": [outbound],
    }

    with tempfile.TemporaryDirectory() as td:
        cfg_path = Path(td) / "cfg.json"
        cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
        proc = subprocess.Popen(
            [XRAY_BIN, "-c", str(cfg_path)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        time.sleep(1.2)  # فرصتی برای بالا آمدن پراکسی
        try:
            r = requests.get(
                TEST_URL,
                proxies={
                    "http": f"socks5h://127.0.0.1:{SOCKS_PORT}",
                    "https": f"socks5h://127.0.0.1:{SOCKS_PORT}",
                },
                timeout=TIMEOUT,
            )
            ok = r.status_code in (200, 204)
        except Exception:
            ok = False
        finally:
            proc.kill()
        return ok


def main() -> None:
    links = fetch_links(RAW_URL)
    good, bad = [], []

    for i, ln in enumerate(links, 1):
        head = ln[:60] + ("…" if len(ln) > 60 else "")
        print(f"[{i}/{len(links)}] تست {head:<60}", end="")
        try:
            if test_link(ln):
                print(" ✔")
                good.append(ln)
            else:
                print(" ❌")
                bad.append(ln)
        except Exception as e:
            print(f" ⚠ {e}")
            bad.append(ln)

    Path(os.path.join(os.path.dirname(__file__), "working.txt")).write_text("\n".join(good), encoding="utf-8")
    Path(os.path.join(os.path.dirname(__file__), "dead.txt")).write_text("\n".join(bad), encoding="utf-8")

    print(f"\n🎯 پایان کار — سالم: {len(good)} | خراب یا نامعتبر: {len(bad)}")


if __name__ == "__main__":
    if not Path(XRAY_BIN).exists():
        sys.exit(f"❌ فایل xray.exe پیدا نشد: {XRAY_BIN}")
    main()
